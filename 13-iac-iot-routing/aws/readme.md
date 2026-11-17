# AWS IoT Core with Amazon S3 - CloudFormation Deployment

This is the AWS version of the [Bicep IoT Hub exercise](../readme.md). You'll deploy an IoT data pipeline using **AWS CloudFormation** (Infrastructure as Code) and learn about **message routing** with **AWS IoT rules**. You'll see how AWS IoT Core can automatically store messages in Amazon S3 based on a property of the message.

| Azure | AWS |
|-------|-----|
| Bicep (`main.bicep`) | CloudFormation template (`template.yaml`) |
| Resource group + deployment (`az deployment group create`) | Stack (`aws cloudformation deploy`) |
| IoT Hub (F1 / S1 tier, partitions) | AWS IoT Core - no hub to create: every account has one endpoint per region; you pay per message |
| Storage account + blob container | S3 bucket |
| Message route with the condition `level="storage"` | IoT rule with the SQL `WHERE get(get_user_properties('level'), 0) = 'storage'` |
| Storage endpoint (batches messages into one blob every 100 s) | S3 rule action (writes one object per message) |
| `fileNameFormat` (`{iothub}/{partition}/{YYYY}/...`) | Object key template (`${topic(2)}/${parse_time(...)}/${newuuid()}.json`) |
| Fallback route → built-in endpoint `messages/events` | No fallback: a message that matches no rule only reaches MQTT subscribers (e.g. the MQTT test client) |
| Custom message properties (`message.custom_properties`) | MQTT 5 user properties (`properties.UserProperty`) |
| Device identity + connection string (SAS token) | Thing + X.509 certificate + IoT policy |
| Azure IoT Device SDK (`azure-iot-device`) | Paho MQTT client (`paho-mqtt`) with MQTT 5 |
| Routing metrics (Azure Monitor) | CloudWatch metrics of the rule (`TopicMatch`, `Success`, `Failure`) |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. If your account is limited to one region (for example a new AWS account with a selected Region), use that region instead. AWS IoT Core, Amazon S3 and CloudFormation are Free Tier eligible: on accounts created before July 2025 the Free Tier covers 500,000 IoT messages and 2,000 S3 PUT requests per month for 12 months, on newer accounts the costs are paid from your Free Tier credits. The simulator sends one message every 10 seconds, so one hour of running costs a fraction of a cent. Stop the simulator and delete everything at the end of the exercise.

## Architecture Overview

This exercise demonstrates a complete device-to-storage data pipeline:

```
IoT Device (Python Simulator)
    ↓ (MQTT 5 over TLS, X.509 certificate)
AWS IoT Core
    ↓ (IoT rule: selects messages with the user property level=storage)
Amazon S3 (stores each message as a JSON file)
```

### Key Concepts

**IoT rules**: AWS IoT Core runs every message through the rules of the account. A rule has an SQL statement that selects messages and builds the output, and actions that send the output somewhere (S3, DynamoDB, Lambda, ...). The SQL can filter on:
- The topic (`FROM 'devices/+/messages/events/'`)
- The message body (`WHERE temperature > 25`)
- MQTT 5 properties (`get_user_properties('level')`)
- The device ID in the topic (`topic(2)`)

In this exercise, messages with the MQTT 5 user property `level=storage` are stored in S3.

### What You'll Learn

- How to deploy IoT infrastructure using CloudFormation
- Understanding AWS IoT rules: SQL filters and actions
- Working with MQTT 5 user properties (the counterpart of IoT Hub custom properties)
- How AWS IoT Core automatically stores messages in Amazon S3
- CloudFormation resource dependencies and outputs
- Device authentication with X.509 certificates

## Tested Environments

- AWS CloudShell (Bash)
- Ubuntu 24.04/26.04, Python 3.10+ (tested with 3.12, `paho-mqtt` 1.6.1)

## Prerequisites

Before starting, ensure you have:
- An AWS account (see [`1-cloud-account/aws`](../../1-cloud-account/aws/readme.md))
- Python 3.10 or higher installed
- VS Code installed
- Basic understanding of AWS IoT Core (complete the [AWS version of Exercise 6](../../6-paas-iot-mqtt/aws/readme.md) first)
- Basic understanding of CloudFormation (complete the [AWS version of Exercise 12](../../12-iac-serverless-functions/aws/readme.md) first)

---

## Part 1: Understand the CloudFormation Template

### Step 1: Examine the CloudFormation Template

Open [`template.yaml`](template.yaml) and review its structure. This template creates four resources:

**Parameters** (lines 6-11):

```yaml
Parameters:
  ProjectName:
    Type: String
    Default: contoso
    AllowedPattern: '[a-z][a-z0-9]{0,10}'
```

- `ProjectName`: Prefix of the rule name (1-11 lowercase letters and digits; `AllowedPattern` rejects other values before anything is created)

There are no parameters for the tier or the partitions: AWS IoT Core has no hub to size, it scales by itself.

**Resources Deployed**:

1. **ResultsBucket** (lines 14-26): The S3 bucket for the telemetry. It has no name in the template, so CloudFormation generates a unique one from the stack name (like `uniqueString()` in Bicep). Public access is blocked and the objects are encrypted
2. **ResultsBucketPolicy** (lines 28-45): Denies any access to the bucket without HTTPS
3. **StorageRouteRole** (lines 47-68): The IAM role of the rule: AWS IoT (from your account only) may put objects into the bucket - nothing else
4. **StorageRoute** (lines 70-87): The IoT rule, the counterpart of the IoT Hub route with its storage endpoint

**Key CloudFormation Features Demonstrated**:

**The rule SQL** (lines 79-82):
```sql
SELECT *, topic(2) AS device_id, timestamp() AS received_at
FROM 'devices/+/messages/events/'
WHERE get(get_user_properties('level'), 0) = 'storage'
```
- `FROM`: the topics of all devices (`+` matches one topic level, the device ID)
- `SELECT *`: the whole message body, plus the device ID (the second level of the topic) and the time AWS IoT received the message (in milliseconds)
- `WHERE`: only messages whose user property `level` is `storage`. `get_user_properties('level')` returns a list (a property can repeat), `get(..., 0)` takes its first value

**The S3 action and the object key** (lines 83-87):
```yaml
Key: ${topic(2)}/${parse_time("yyyy/MM/dd/HH/mm", timestamp())}/${newuuid()}.json
```
This creates an organized folder structure in S3 by device and date/time, like `fileNameFormat` in Bicep. `newuuid()` gives each message its own file name. (The `${...}` here are substitution templates of AWS IoT, not of CloudFormation: without `!Sub`, CloudFormation leaves them as they are.)

**Outputs** (lines 89-95):
```yaml
Outputs:
  BucketName:
    Value: !Ref ResultsBucket
  RuleName:
    Value: !Ref StorageRoute
```
Outputs provide important information after deployment.

---

## Part 2: Deploy Infrastructure with CloudFormation

### Step 2: Prepare AWS CloudShell

Open **AWS CloudShell** from the AWS Console (the terminal icon in the top bar), in the region you want to use.

**Option A: Using Bash (recommended)**

**Set the stack name:**

```bash
STACK_NAME="cloud-computing-iot-core"
```

Set the AWS region (change if needed):

```bash
REGION="eu-west-2"
```

Set the project name (1-11 lowercase letters and digits, used as prefix):

```bash
PROJECT_NAME="contoso"
```

**Download the template:**

```bash
curl -o template.yaml https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/13-iac-iot-routing/aws/template.yaml
```

### Step 3: Deploy the CloudFormation Template

**Option A: Using Bash (recommended)**

**Deploy the S3 bucket and the IoT rule:**

```bash
aws cloudformation deploy \
  --region $REGION \
  --stack-name $STACK_NAME \
  --template-file template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides ProjectName=$PROJECT_NAME
```

**Wait about 1 minute for deployment to complete**. You'll see `Successfully created/updated stack - cloud-computing-iot-core`.

**View deployment outputs:**

```bash
aws cloudformation describe-stacks \
  --region $REGION \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs" \
  --output table
```

This shows the bucket name and the rule name.

**Option B: Using PowerShell**

Start PowerShell in AWS CloudShell by typing `pwsh`.

**Set the stack name:**

```powershell
$STACK_NAME="cloud-computing-iot-core"
```

Set the AWS region (change if needed):

```powershell
$REGION="eu-west-2"
```

Set the project name (1-11 lowercase letters and digits, used as prefix):

```powershell
$PROJECT_NAME="contoso"
```

**Download the template:**

```powershell
curl -o template.yaml https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/13-iac-iot-routing/aws/template.yaml
```

**Deploy the S3 bucket and the IoT rule:**

```powershell
aws cloudformation deploy `
  --region $REGION `
  --stack-name $STACK_NAME `
  --template-file template.yaml `
  --capabilities CAPABILITY_IAM `
  --parameter-overrides ProjectName=$PROJECT_NAME
```

**Wait about 1 minute for deployment to complete**. You'll see `Successfully created/updated stack - cloud-computing-iot-core`.

**View deployment outputs:**

```powershell
aws cloudformation describe-stacks `
  --region $REGION `
  --stack-name $STACK_NAME `
  --query "Stacks[0].Outputs" `
  --output table
```

This shows the bucket name and the rule name.

### Step 4: Verify Deployed Resources

**Option A: Using Bash (recommended)**

**List all resources:**

```bash
aws cloudformation describe-stack-resources \
  --region $REGION \
  --stack-name $STACK_NAME \
  --query "StackResources[].[LogicalResourceId,ResourceType,PhysicalResourceId]" \
  --output table
```

You should see:
- `ResultsBucket` (`AWS::S3::Bucket`, e.g. `cloud-computing-iot-core-resultsbucket-<unique-string>`)
- `ResultsBucketPolicy` (`AWS::S3::BucketPolicy`)
- `StorageRouteRole` (`AWS::IAM::Role`)
- `StorageRoute` (`AWS::IoT::TopicRule`, `contoso_storage_route`)

**Get the bucket name:**

```bash
BUCKET_NAME=$(aws cloudformation describe-stacks --region $REGION --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
echo "Your bucket name: $BUCKET_NAME"
```

**Option B: Using PowerShell**

**List all resources:**

```powershell
aws cloudformation describe-stack-resources `
  --region $REGION `
  --stack-name $STACK_NAME `
  --query "StackResources[].[LogicalResourceId,ResourceType,PhysicalResourceId]" `
  --output table
```

You should see:
- `ResultsBucket` (`AWS::S3::Bucket`, e.g. `cloud-computing-iot-core-resultsbucket-<unique-string>`)
- `ResultsBucketPolicy` (`AWS::S3::BucketPolicy`)
- `StorageRouteRole` (`AWS::IAM::Role`)
- `StorageRoute` (`AWS::IoT::TopicRule`, `contoso_storage_route`)

**Get the bucket name:**

```powershell
$BUCKET_NAME=$(aws cloudformation describe-stacks --region $REGION --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
echo "Your bucket name: $BUCKET_NAME"
```

---

## Part 3: Create IoT Device and Configure Simulator

### Step 5: Register Device in AWS IoT Core

The steps are the same as in Exercise 6, with a new device name. Like the device identity in the Azure version, the device is created with the CLI, not with the template.

**Option A: Using Bash (recommended)**

**Set the device name** (the thing name, also used as the MQTT client ID):

```bash
THING_NAME="my-cfn-device-01"
```

Save your AWS account ID (used in the policy):

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**Register your device (create a thing):**

```bash
aws iot create-thing --region $REGION --thing-name $THING_NAME
```

**Create the device certificate and private key, and save the certificate's ARN:**

```bash
CERTIFICATE_ARN=$(aws iot create-keys-and-certificate \
  --region $REGION \
  --set-as-active \
  --certificate-pem-outfile device.pem.crt \
  --private-key-outfile private.pem.key \
  --query certificateArn \
  --output text)
```

**Create an IoT policy that allows the device to connect with its own client ID and publish to its own topics:**

```bash
cat > device-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:topic/devices/$THING_NAME/*"}
  ]
}
EOF
```

```bash
aws iot create-policy \
  --region $REGION \
  --policy-name ${THING_NAME}-policy \
  --policy-document file://device-policy.json
```

**Attach the policy to the certificate, and the certificate to the thing:**

```bash
aws iot attach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
```

```bash
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```

**Show your IoT Core endpoint (the MQTT broker hostname):**

```bash
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

**Important:** Copy the **endpoint** - you'll need it for the device simulator.

**Option B: Using PowerShell**

**Set the device name** (the thing name, also used as the MQTT client ID):

```powershell
$THING_NAME="my-cfn-device-01"
```

Save your AWS account ID (used in the policy):

```powershell
$ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**Register your device (create a thing):**

```powershell
aws iot create-thing --region $REGION --thing-name $THING_NAME
```

**Create the device certificate and private key, and save the certificate's ARN:**

```powershell
$CERTIFICATE_ARN=$(aws iot create-keys-and-certificate `
  --region $REGION `
  --set-as-active `
  --certificate-pem-outfile device.pem.crt `
  --private-key-outfile private.pem.key `
  --query certificateArn `
  --output text)
```

**Create an IoT policy that allows the device to connect with its own client ID and publish to its own topics:**

```powershell
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:topic/devices/$THING_NAME/*"}
  ]
}
"@ | Set-Content device-policy.json
```

```powershell
aws iot create-policy `
  --region $REGION `
  --policy-name "$THING_NAME-policy" `
  --policy-document file://device-policy.json
```

**Attach the policy to the certificate, and the certificate to the thing:**

```powershell
aws iot attach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
```

```powershell
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```

**Show your IoT Core endpoint (the MQTT broker hostname):**

```powershell
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

**Important:** Copy the **endpoint** - you'll need it for the device simulator.

### Step 6: Configure Device Simulator

**Download the certificate and the private key from CloudShell:**
1. In CloudShell, click **"Actions"** → **"Download file"**
2. Enter `/home/cloudshell-user/device.pem.crt` and click **"Download"**
3. Repeat for `/home/cloudshell-user/private.pem.key`
4. Move both files to the `13-iac-iot-routing/aws` folder on your computer

**Important:** The private key is the device's password. Don't share it or commit it to git (the `aws/.gitignore` file already excludes it).

**On your local machine**, navigate to the AWS folder of the exercise:

```bash
cd 13-iac-iot-routing/aws
```

**Create Python virtual environment:**

**On macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows:**

```powershell
py -m venv .venv
.venv\scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

This installs the Paho MQTT client `paho-mqtt` version 1.6.1 (the same as in Exercise 6).

**Update the endpoint:**

Open `simple_aws_device_simulator.py` and update line 15:

```python
iot_endpoint = "abcdefgh123456-ats.iot.eu-west-2.amazonaws.com"  # Your IoT Core endpoint
```

Paste your endpoint from Step 5. The device ID on line 14 (`my-cfn-device-01`) must be the same as the thing name.

### Step 7: Understand the Device Simulator Code

The simulator has two key features:

**1. Uses MQTT 5 with a certificate** (lines 25-29):
```python
client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv5)
client.tls_set(ca_certs=path_to_root_cert, certfile=path_to_device_cert, keyfile=path_to_private_key, ...)
```
MQTT 5 is the version of MQTT that can carry **user properties** - key-value pairs next to the message body. Exercise 6 used MQTT 3.1.1, which has no properties.

**2. Adds a User Property** (lines 60-63):
```python
properties = Properties(PacketTypes.PUBLISH)
properties.ContentType = "application/json"
properties.UserProperty = ("level", "storage")
client.publish(topic, message, qos=1, properties=properties)
```
The user property `level=storage` triggers the rule defined in the CloudFormation template - like `message.custom_properties["level"] = "storage"` in the Azure version!

**Message Routing Logic:**
- Messages WITH `level=storage` → Stored in S3 by the rule
- Messages WITHOUT this property → Not stored; only devices and apps subscribed to the topic receive them

---

## Part 4: Run Simulator and Verify Data Flow

### Step 8: Run the Device Simulator

**Start the simulator:**

```bash
python simple_aws_device_simulator.py
```

You should see output like:

```
Connecting to AWS IoT
MQTT topic: devices/my-cfn-device-01/messages/events/
Connected to AWS IoT with result code: Success
Message sent: {"temperature": 26.637717433228474, "humidity": 49.184963361324705, "pressure": 922.3005652879709}
Message sent: {"temperature": 25.332355650533767, "humidity": 49.988567938773855, "pressure": 1073.9131653399668}
```

The simulator sends telemetry every 10 seconds. **Keep it running** for at least 1 minute.

### Step 9: Check the Rule in the AWS Console

**View the rule configuration:**

1. In the AWS Console, open **AWS IoT Core** → **Message routing** → **Rules**
2. Click `contoso_storage_route`
3. Review the **SQL statement** - you'll see the `WHERE` condition with `level`
4. Review the **Actions** - you'll see the S3 bucket and the key

**View the rule metrics:**

1. Open **CloudWatch** → **Metrics** → **All metrics** → **IoT**
2. Select **TopicMatch** with the dimension `RuleName` = `contoso_storage_route` - all messages published to the topic of the rule (before the `WHERE` filter)
3. Select **Success** and **Failure** with the dimensions `RuleName` = `contoso_storage_route` and `ActionType` = `S3` - the messages written to S3 (after the filter) and the failed writes
4. Set the statistic to **Sum** (metrics appear with a delay of 1-3 minutes)

### Step 10: Verify Data in S3

Unlike IoT Hub, which collects messages for 100 seconds and writes them to one blob, the rule writes **each message as a separate object right away**.

**Option 1: Via AWS Console**

1. Open **S3** → **Buckets** → your bucket (`cloud-computing-iot-core-resultsbucket-...`)
2. Navigate through the folder hierarchy: `my-cfn-device-01/YYYY/MM/DD/HH/mm/`
3. Select one of the JSON files and click **Download** (or **Open**)

**Option 2: Via AWS CLI**

**Using Bash:**

**List objects in the bucket:**

```bash
aws s3 ls s3://$BUCKET_NAME --recursive --region $REGION
```

**Download an object to inspect:**

```bash
# Get the first object key
OBJECT_KEY=$(aws s3api list-objects-v2 \
  --bucket $BUCKET_NAME \
  --region $REGION \
  --query "Contents[0].Key" \
  --output text)

# Download the object
aws s3 cp s3://$BUCKET_NAME/$OBJECT_KEY downloaded-telemetry.json --region $REGION

# View the content
cat downloaded-telemetry.json
```

**Using PowerShell:**

**List objects in the bucket:**

```powershell
aws s3 ls s3://$BUCKET_NAME --recursive --region $REGION
```

**Download an object to inspect:**

```powershell
# Get the first object key
$OBJECT_KEY=$(aws s3api list-objects-v2 `
  --bucket $BUCKET_NAME `
  --region $REGION `
  --query "Contents[0].Key" `
  --output text)

# Download the object
aws s3 cp "s3://$BUCKET_NAME/$OBJECT_KEY" downloaded-telemetry.json --region $REGION

# View the content
cat downloaded-telemetry.json
```

**Expected content:**

```json
{"temperature":25.332355650533767,"humidity":49.988567938773855,"pressure":1073.9131653399668,"device_id":"my-cfn-device-01","received_at":1794935509264}
```

Each file contains one message: the body sent by the device plus the two fields added by the rule SQL (`device_id` from the topic, `received_at` in milliseconds since 1970). IoT Hub instead wraps every message in an envelope with `Properties`, `SystemProperties` and `Body`.

---

## Part 5: Explore Message Routing

### Step 11: Experiment with Message Routing

**Modify the device simulator to send different message types:**

Open `simple_aws_device_simulator.py` and modify the user property:

**Option 1: Remove the routing property**

Comment out line 62:
```python
# properties.UserProperty = ("level", "storage")
```

Restart the simulator. The messages still arrive in AWS IoT Core, but the rule doesn't select them, so no new files appear in S3.

**Option 2: Add multiple properties**

Add different properties for more complex routing:
```python
properties.UserProperty = [("level", "storage"), ("sensor_type", "temperature"), ("location", "warehouse-1")]
```

and use them in the rule SQL, e.g. `WHERE get(get_user_properties('location'), 0) = 'warehouse-1'`.

**Option 3: Conditional routing based on values**

```python
if temperature > 25:
    properties.UserProperty = [("level", "storage"), ("alert", "high-temp")]
```

Or filter on the body in the rule itself: `WHERE temperature > 25` - IoT rules can read the JSON body, IoT Hub routes too (`$body.temperature > 25`).

### Step 12: View All Messages in the MQTT Test Client

AWS IoT has no fallback route: a message that matches no rule goes only to the devices and apps subscribed to its topic. To see all messages - also the ones without the property:

1. In the AWS Console, open **AWS IoT Core** → **MQTT test client**
2. In **Subscribe to a topic**, enter `devices/+/messages/events/` and click **Subscribe**
3. Remove the user property from the simulator (Option 1 in Step 11) and restart it
4. You'll see the messages appear in the test client, while no new files appear in S3

**Compare the counts in CloudWatch** (Step 9): **TopicMatch** of the rule counts all messages on the topic, **Success** of its `S3` action counts only those with `level=storage`. After a run with and without the property, `TopicMatch` is higher than `Success`.

---

## Understanding the Deployment

### CloudFormation Resource Dependencies

The template automatically handles dependencies:

```
S3 Bucket (created first)
    ↓
Bucket Policy (!Ref ResultsBucket)      IAM Role (!GetAtt ResultsBucket.Arn in its policy)
                                            ↓
                                        IoT Rule (!Ref ResultsBucket, !GetAtt StorageRouteRole.Arn)
```

CloudFormation uses implicit dependencies through `!Ref`, `!GetAtt` and `!Sub` - like Bicep does through resource references. When you delete the stack, it deletes the resources in the reverse order.

### AWS IoT Core vs Azure IoT Hub Pricing

| | Azure IoT Hub F1 | Azure IoT Hub S1 | AWS IoT Core |
|---|---|---|---|
| Cost | Free | ~$25/month per unit | ~$1 per million messages + ~$0.08 per million connection minutes |
| Limit | 8,000 messages per day, 1 per subscription | 400,000 messages per day per unit | Scales automatically |
| Routing / rules | Included | Included | ~$0.15 per million rules triggered and actions executed |

Check the current prices for your region: [AWS IoT Core pricing](https://aws.amazon.com/iot-core/pricing/).

### Message Routing Best Practices

1. **Use specific conditions**: Avoid storing all messages (more S3 requests and storage)
2. **Batching**: The S3 action writes one object per message - fine for a few devices; for many devices use Amazon Data Firehose to batch messages into larger files (not in the Free Tier)
3. **Error action**: Add an `ErrorAction` to the rule (e.g. to CloudWatch Logs) to see why a write failed
4. **File format**: JSON is readable, Parquet (via Firehose) is more efficient for analytics
5. **Monitoring**: Set up CloudWatch alarms on the `Failure` metric of the rule

---

## Troubleshooting

### No data appearing in S3

- **Check the user property**: Ensure `properties.UserProperty = ("level", "storage")` is set and the client uses `mqtt.MQTTv5` (MQTT 3.1.1 has no user properties)
- **Check the topic**: The rule reads `devices/+/messages/events/` - the simulator prints its topic at start
- **Check the metrics**: `TopicMatch` of the rule shows if messages arrive on its topic, `Success` / `Failure` of the `S3` action show the stored messages and the failed writes
- **Check the MQTT test client**: Subscribe to `devices/#` to see if messages arrive at all

### Device connection fails

- **Check the endpoint**: Use the `-ats` endpoint from `aws iot describe-endpoint --endpoint-type iot:Data-ATS`
- **Check the certificate files**: `device.pem.crt`, `private.pem.key` and `AmazonRootCA1.pem` must be in the folder you run the simulator from
- **Check the client ID**: `device_id` in the simulator must be the thing name - the IoT policy allows only `client/my-cfn-device-01`
- **Check the certificate**: It must be `ACTIVE` and have the policy attached (`aws iot list-attached-policies --target $CERTIFICATE_ARN --region $REGION`)
- **Network issues**: Ensure your firewall allows outbound traffic on port 8883

### Deployment fails with "The provided function ... does not exist" or a SQL error

- **Check the rule SQL**: Function names are exact (`get_user_properties`, plural); test the SQL in the console (**Rules** → **Create rule**) before putting it into the template

### Stack is in `ROLLBACK_COMPLETE` state

- **The first deployment failed** and CloudFormation deleted the resources. Find the reason:
  ```bash
  aws cloudformation describe-stack-events --region $REGION --stack-name $STACK_NAME --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" --output table
  ```
- **Delete the stack** (`aws cloudformation delete-stack --region $REGION --stack-name $STACK_NAME`) and deploy again

### Deployment fails with "ProjectName ... must match pattern"

- **Use lowercase letters and digits only**, starting with a letter, 1-11 characters

---

## Cleanup

**Important:** Delete all resources to avoid charges! Stop the simulator first (**Ctrl+C**).

### Step 1: Delete the Device

**Using Bash:**

```bash
CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
aws iot detach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
aws iot delete-thing --region $REGION --thing-name $THING_NAME
aws iot delete-policy --region $REGION --policy-name ${THING_NAME}-policy
```

**Using PowerShell:**

```powershell
$CERTIFICATE_ID=$CERTIFICATE_ARN.Split("/")[-1]
aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
aws iot detach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
aws iot delete-thing --region $REGION --thing-name $THING_NAME
aws iot delete-policy --region $REGION --policy-name "$THING_NAME-policy"
```

### Step 2: Empty the Bucket and Delete the Stack

CloudFormation can't delete a bucket with objects in it, so empty the bucket first. Deleting the stack then deletes the bucket, the bucket policy, the role and the rule.

**Using Bash:**

```bash
aws s3 rm s3://$BUCKET_NAME --recursive --region $REGION
aws cloudformation delete-stack --region $REGION --stack-name $STACK_NAME
aws cloudformation wait stack-delete-complete --region $REGION --stack-name $STACK_NAME
```

**Using PowerShell:**

```powershell
aws s3 rm s3://$BUCKET_NAME --recursive --region $REGION
aws cloudformation delete-stack --region $REGION --stack-name $STACK_NAME
aws cloudformation wait stack-delete-complete --region $REGION --stack-name $STACK_NAME
```

**Delete the local files** with the device certificate and key (in CloudShell and on your computer):

```bash
rm -f device.pem.crt private.pem.key device-policy.json template.yaml
```

---

## Summary and Learning Outcomes

Congratulations! You've deployed an IoT data pipeline using CloudFormation. You learned:

✅ **CloudFormation for IoT**: Deploying an S3 bucket and an IoT rule using Infrastructure as Code
✅ **IoT Rules**: Selecting messages with SQL and storing them with an action
✅ **MQTT 5**: Using user properties for routing decisions
✅ **S3 Integration**: Automatic storage of IoT telemetry
✅ **X.509 Certificates**: Authenticating a device without passwords
✅ **Resource Dependencies**: How CloudFormation manages deployment order
✅ **CloudFormation Outputs**: Retrieving resource information after deployment

### Architecture Pattern: Cold Path Storage

This exercise demonstrates the **Cold Path** pattern in IoT:
- **Hot Path**: Real-time processing (IoT rules to Lambda, DynamoDB - Exercise 11)
- **Cold Path**: Historical storage for analytics (S3, data lakes)

Messages are automatically archived to S3 for:
- Long-term storage
- Batch analytics (e.g. Amazon Athena can query the JSON files with SQL)
- Machine learning training data
- Compliance and auditing
- Cost-effective historical queries

### Comparison: Exercise 6 vs Exercise 13

| Feature | Exercise 6 (Manual) | Exercise 13 (CloudFormation) |
|---------|---------------------|------------------------------|
| Deployment | CLI commands | Template (repeatable) for the cloud side, CLI for the device |
| Protocol | MQTT 3.1.1 | MQTT 5 (user properties) |
| Message Routing | Not configured | IoT rule to S3 |
| Infrastructure | Manual setup | Version controlled |
| Time to Deploy | 15-20 minutes | 3-5 minutes |

## Optional Next Steps

- Add a second rule to the template (e.g. messages with `alert=high-temp` to an SNS topic for e-mail notifications)
- Add an `ErrorAction` that writes failed messages to CloudWatch Logs
- Create the thing and the IoT policy in the template too (`AWS::IoT::Thing`, `AWS::IoT::Policy`)
- Add an S3 lifecycle rule (`LifecycleConfiguration`) that deletes telemetry older than 30 days
- Query the JSON files with Amazon Athena
- Compare this exercise with Exercise 15 (Terraform) - same architecture, different IaC tool
- Add a Lambda function triggered by new S3 objects for automatic processing

## Additional Resources

- [AWS IoT rules](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html)
- [AWS IoT SQL functions (`get_user_properties`, `topic`, `parse_time`)](https://docs.aws.amazon.com/iot/latest/developerguide/iot-sql-functions.html)
- [S3 rule action](https://docs.aws.amazon.com/iot/latest/developerguide/s3-rule-action.html)
- [AWS::IoT::TopicRule reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-iot-topicrule.html)
- [AWS IoT Core pricing](https://aws.amazon.com/iot-core/pricing/)

---

## Reference: CloudFormation Template Structure

**Key sections in template.yaml:**

```yaml
# 1. Parameters - User inputs
Parameters:
  ProjectName:
    Default: contoso

# 2. Resources - What to deploy
Resources:
  ResultsBucket:
    Type: AWS::S3::Bucket
  StorageRoute:
    Type: AWS::IoT::TopicRule

# 3. Outputs - Return values
Outputs:
  BucketName:
    Value: !Ref ResultsBucket
```

**Common CloudFormation functions used:**

- `!Ref` - Parameter value, or the name / ID of a resource
- `!GetAtt` - Attribute of a resource (e.g. the ARN)
- `!Sub` - Build a string with variables (`${ProjectName}_storage_route`)
- `AWS::AccountId` - Pseudo parameter with your account ID
