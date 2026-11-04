# Serverless IoT Platform

This is the AWS version of the [Azure serverless IoT platform exercise](../readme.md). You'll build a complete serverless IoT platform combining five AWS services: IoT devices send telemetry data that flows through AWS services and can be queried via a REST API.

| Azure | AWS |
|-------|-----|
| Azure IoT Hub + device identity + SAS token | AWS IoT Core + thing + X.509 certificate (as in [exercise 6](../../6-paas-iot-mqtt/aws/readme.md)) |
| Azure Stream Analytics job (input, query, output) | AWS IoT rule: an SQL query and a DynamoDB action, part of IoT Core |
| Azure Cosmos DB: database with 3 containers | Amazon DynamoDB: 3 tables (no database level) |
| Partition key `/deviceid` | Partition key `deviceid` + sort key `timestamp` |
| Cosmos DB endpoint and key in the app settings | IAM role of the functions - no database key at all |
| Function App with 3 functions (`device`, `house`, `rooms`) | 3 AWS Lambda functions behind an Amazon API Gateway HTTP API |
| `https://<app>.azurewebsites.net/api/device` | `https://<api-id>.execute-api.<region>.amazonaws.com/api/device` |
| Function key (`?code=<key>`) | API key checked by the functions (`?code=<key>`), stored in an environment variable |
| CORS headers in the function code | CORS configuration of the HTTP API |
| Azure Static Web Apps (optional frontend) | S3 static website (optional frontend, as in [exercise 8](../../8-storage-static-website/aws/readme.md)) |
| Resource group | No direct equivalent - resources are deleted one by one |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. AWS IoT Core, DynamoDB (25 GB, 25 read and 25 write capacity units - the three tables use 15 of each), Lambda (1 million requests per month) and S3 are Free Tier eligible. API Gateway HTTP APIs are free for 1 million calls per month for 12 months on accounts with the legacy Free Tier; on newer accounts they are paid from your Free Tier credits (about $1 per million calls). Delete all resources at the end of the exercise.

## Architecture Overview

```
IoT Device (Simulator)
    ↓ (MQTTS, X.509 certificate)
AWS IoT Core (receives telemetry)
    ↓ (IoT rule: SQL query + DynamoDB action)
Amazon DynamoDB (NoSQL storage)
    ↑ (queries data)
AWS Lambda functions (REST API)
    ↑ (HTTPS)
Amazon API Gateway (HTTP API)
    ↑ (HTTP requests)
Client (Postman / curl / Frontend)
```

### What You'll Learn
- How to connect a device to AWS IoT Core
- How to process and store IoT messages with an AWS IoT rule (instead of a separate stream processing service)
- How to store IoT data in Amazon DynamoDB (NoSQL database)
- How to build a REST API using AWS Lambda (serverless compute) and Amazon API Gateway
- How to give services access to each other with IAM roles instead of keys
- How to test REST APIs using Postman or curl

## Tested Environments
- Ubuntu 26.04
- Python 3.10+ (device simulator), Lambda runtime Python 3.13
- Node.js 20+ (optional frontend)

## Prerequisites

Before starting, ensure you have:
- An AWS account (see [1-cloud-account/aws](../../1-cloud-account/aws/readme.md))
- [VS Code](https://code.visualstudio.com/) installed
- [Postman](https://www.postman.com/) for API testing (or `curl`)
- Completed [Exercise 6 (AWS IoT Core)](../../6-paas-iot-mqtt/aws/readme.md) - we'll reuse the device simulator

---

## Part 1: Connect a Device to AWS IoT Core and Send Test Data

### Step 1: Register Your Device

Open **AWS CloudShell** (the terminal icon in the AWS Console's top bar). The steps are the same as in exercise 6, with a new device name.

**Option A: Using Bash (recommended)**

**Set the environment variables one by one:**

Set the AWS region (change if needed):
```bash
REGION="eu-west-2"
```

Set your device name (the thing name, also used as the MQTT client ID):
```bash
THING_NAME="my-iot-device-01"
```

Save your AWS account ID (used in the policies):
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

Start PowerShell in AWS CloudShell by typing `pwsh`.

**Set the environment variables one by one:**

Set the AWS region (change if needed):
```powershell
$REGION="eu-west-2"
```

Set your device name (the thing name, also used as the MQTT client ID):
```powershell
$THING_NAME="my-iot-device-01"
```

Save your AWS account ID (used in the policies):
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

### Step 2: Configure and Run Device Simulator

We'll reuse the AWS device simulator from Exercise 6.

**Download the certificate and the private key from CloudShell:**
1. In CloudShell, click **"Actions"** → **"Download file"**
2. Enter `/home/cloudshell-user/device.pem.crt` and click **"Download"**
3. Repeat for `/home/cloudshell-user/private.pem.key`
4. Move both files to the `6-paas-iot-mqtt/aws` folder on your computer (replace the files from exercise 6, if they are still there)

**Important:** The private key is the device's password. Don't share it or commit it to git (the `aws/.gitignore` file already excludes it).

**On your local machine**, navigate to the AWS simulator of Exercise 6:
```bash
cd 6-paas-iot-mqtt/aws
```

If you haven't already, create a virtual environment and install dependencies:

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

**On Windows:**
```powershell
py -m venv .venv
.venv\scripts\activate
pip install -r ..\requirements.txt
```

**Configure the simulator:**

Open `simple_mqtt_device_simulator.py` and update these values.

Set your device ID - it **must be the same as the thing name**:
```python
device_id = "my-iot-device-01"
```

**Uncomment the security lines** (remove the `#` at the start):
```python
client.tls_set(ca_certs=path_to_root_cert, certfile=path_to_device_cert, keyfile=path_to_private_key,
               cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
client.tls_insecure_set(False)
```

Update the connection settings to use your IoT Core endpoint and the secure port:
```python
mqtt_hub_hostname = "abcdefgh123456-ats.iot.eu-west-2.amazonaws.com"  # Your IoT Core endpoint
mqtt_hub_port = 8883  # Secure MQTT port (MQTTS)
```

**Run the simulator:**
```bash
python simple_mqtt_device_simulator.py
```

You should see messages like:
```
Device connected with result code: 0
Device sent message
Message sent: {"device_id": "my-iot-device-01", "temperature": 25.3, "humidity": 52.1, "pressure": 1013.2, "timestamp": 1705340123.456}
```

The device publishes to the topic `devices/my-iot-device-01/messages/events/`. You can watch the messages in the AWS Console: **AWS IoT Core** → **MQTT test client** → subscribe to `devices/#`.

**Keep the simulator running** - we need continuous data for testing later.

---

## Part 2: Create DynamoDB Tables

DynamoDB is a serverless NoSQL database that will store our IoT data and entities. Unlike Cosmos DB, there is no account or database to create: tables belong directly to your account and region.

### Step 3: Create the Tables

Go back to **AWS CloudShell**. The commands are the same in Bash and PowerShell (in PowerShell, replace the `\` at the end of the lines with a backtick `` ` ``).

**Create the table for IoT telemetry data.** The partition key `deviceid` groups the readings of one device, and the sort key `timestamp` (a number, `N`) orders them. Together they are the primary key, so every reading needs a different timestamp:
```bash
aws dynamodb create-table \
  --region $REGION \
  --table-name iot-data \
  --attribute-definitions AttributeName=deviceid,AttributeType=S AttributeName=timestamp,AttributeType=N \
  --key-schema AttributeName=deviceid,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

**Create the table for house data** (the key is `id`):
```bash
aws dynamodb create-table \
  --region $REGION \
  --table-name house-data \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

**Create the table for room data** (the key is `id`):
```bash
aws dynamodb create-table \
  --region $REGION \
  --table-name room-data \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

**Wait until the tables are ready** (about 20 seconds):
```bash
aws dynamodb wait table-exists --region $REGION --table-name iot-data
```
```bash
aws dynamodb wait table-exists --region $REGION --table-name house-data
```
```bash
aws dynamodb wait table-exists --region $REGION --table-name room-data
```

Each table uses 5 read and 5 write capacity units - 15 of each in total, within the Free Tier of 25.

---

## Part 3: Create an AWS IoT Rule

In Azure, a separate Stream Analytics job reads the messages from IoT Hub, transforms them with an SQL query and writes them to Cosmos DB. In AWS, this is part of IoT Core: an **IoT rule** has an SQL query that selects messages from MQTT topics, and **actions** that send the result to other services - here, a DynamoDB table.

### Step 4: Create the Role of the Rule

The rule needs permission to write to the `iot-data` table. In AWS, one service gets access to another through an **IAM role** - not a key. The trust policy lets IoT Core use the role, only for your account (`aws:SourceAccount`), and the permissions policy allows only `PutItem` on one table.

**Option A: Using Bash (recommended)**

```bash
cat > iot-rule-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "iot.amazonaws.com"}, "Action": "sts:AssumeRole",
                 "Condition": {"StringEquals": {"aws:SourceAccount": "$ACCOUNT_ID"}}}]
}
EOF
```
```bash
IOT_RULE_ROLE_ARN=$(aws iam create-role \
  --role-name iot-data-to-dynamodb-role \
  --assume-role-policy-document file://iot-rule-trust-policy.json \
  --query Role.Arn \
  --output text)
```
```bash
cat > iot-rule-dynamodb-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/iot-data"}]
}
EOF
```
```bash
aws iam put-role-policy \
  --role-name iot-data-to-dynamodb-role \
  --policy-name write-iot-data \
  --policy-document file://iot-rule-dynamodb-policy.json
```

**Option B: Using PowerShell**

```powershell
@"
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "iot.amazonaws.com"}, "Action": "sts:AssumeRole",
                 "Condition": {"StringEquals": {"aws:SourceAccount": "$ACCOUNT_ID"}}}]
}
"@ | Set-Content iot-rule-trust-policy.json
```
```powershell
$IOT_RULE_ROLE_ARN=$(aws iam create-role `
  --role-name iot-data-to-dynamodb-role `
  --assume-role-policy-document file://iot-rule-trust-policy.json `
  --query Role.Arn `
  --output text)
```
```powershell
@"
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/iot-data"}]
}
"@ | Set-Content iot-rule-dynamodb-policy.json
```
```powershell
aws iam put-role-policy `
  --role-name iot-data-to-dynamodb-role `
  --policy-name write-iot-data `
  --policy-document file://iot-rule-dynamodb-policy.json
```

### Step 5: Create the Rule

The rule's query does the same as the Stream Analytics query in the Azure version: it reads the messages of all devices (`+` matches any device ID in the topic), selects the sensor values and renames `device_id` to `deviceid`, the partition key of the table. The `dynamoDBv2` action writes every selected field as an attribute of a new item.

**Option A: Using Bash (recommended)**

```bash
cat > iot-rule.json <<EOF
{
  "sql": "SELECT temperature, humidity, pressure, timestamp, device_id AS deviceid FROM 'devices/+/messages/events/'",
  "awsIotSqlVersion": "2016-03-23",
  "ruleDisabled": false,
  "actions": [{"dynamoDBv2": {"putItem": {"tableName": "iot-data"}, "roleArn": "$IOT_RULE_ROLE_ARN"}}]
}
EOF
```

Create the rule. If it fails with `iot.amazonaws.com is unable to perform: sts:AssumeRole`, the new role isn't ready yet: wait 10 seconds and try again:
```bash
aws iot create-topic-rule \
  --region $REGION \
  --rule-name iot_data_to_dynamodb \
  --topic-rule-payload file://iot-rule.json
```

**Option B: Using PowerShell**

```powershell
@"
{
  "sql": "SELECT temperature, humidity, pressure, timestamp, device_id AS deviceid FROM 'devices/+/messages/events/'",
  "awsIotSqlVersion": "2016-03-23",
  "ruleDisabled": false,
  "actions": [{"dynamoDBv2": {"putItem": {"tableName": "iot-data"}, "roleArn": "$IOT_RULE_ROLE_ARN"}}]
}
"@ | Set-Content iot-rule.json
```

Create the rule. If it fails with `iot.amazonaws.com is unable to perform: sts:AssumeRole`, the new role isn't ready yet: wait 10 seconds and try again:
```powershell
aws iot create-topic-rule `
  --region $REGION `
  --rule-name iot_data_to_dynamodb `
  --topic-rule-payload file://iot-rule.json
```

The rule starts working at once - there is no job to start.

### Step 6: Verify Data Flow

**Check if data is flowing into DynamoDB:**

1. In the AWS Console, go to **DynamoDB** → **Tables** → `iot-data` → **Explore table items**
2. You should see items with `deviceid`, `timestamp`, `temperature`, `humidity` and `pressure`, a new one every 10 seconds

Or in CloudShell (the same in Bash and PowerShell):
```bash
aws dynamodb scan --region $REGION --table-name iot-data --max-items 5 --query "Items[].[deviceid.S,timestamp.N,temperature.N]" --output table
```

If you see data, congratulations! Your data pipeline is working:
**Device → IoT Core → IoT rule → DynamoDB**

---

## Part 4: Create the REST API with AWS Lambda and API Gateway

Now we'll create a serverless REST API to query and manage the IoT data: three Lambda functions, one for each endpoint, and an HTTP API in API Gateway that gives them one public address.

### Step 7: Look at the Function Code

The code is in the `aws/iot-lambda-api` folder:
- `device.py` - `GET /api/device?device_id=...`: queries all readings of one device (the partition key) from `iot-data`
- `house.py` - `GET /api/house?house_id=...` reads one house, `POST /api/house` creates one in `house-data`
- `rooms.py` - `GET /api/rooms?room_id=...` reads one room, `POST /api/rooms` creates one in `room-data`
- `common.py` - shared helpers: the API key check, reading the request, and writing the JSON response

Compared with the Azure functions:
- There is no database endpoint or key to configure. `boto3` uses the IAM role of the function, which may only read and write these three tables
- Azure Functions check the function key (`?code=`) before your code runs. HTTP APIs have no API keys, so `common.py` checks the `code` query parameter against the `API_KEY` environment variable. In production you would use an authorizer of API Gateway, for example with Amazon Cognito
- A house or room that already exists returns `409 Conflict`, as in the Azure version (`put_item` with `attribute_not_exists(id)` instead of Cosmos DB's `create_item`)

### Step 8: Create the Lambda Functions

In **AWS CloudShell**:

**Option A: Using Bash (recommended)**

**Download the function code:**
```bash
mkdir iot-lambda-api
```
```bash
for FILE in common device house rooms; do
  curl -o iot-lambda-api/$FILE.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/11-serverless-iot-platform/aws/iot-lambda-api/$FILE.py
done
```

**Generate an API key** (32 random hexadecimal characters) and save it - you'll need it in every request:
```bash
API_KEY=$(openssl rand -hex 16)
```
```bash
echo $API_KEY
```

**Create the execution role of the functions.** `AWSLambdaBasicExecutionRole` allows writing logs, and the inline policy allows reading and writing only the three tables:
```bash
cat > lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
EOF
```
```bash
LAMBDA_ROLE_ARN=$(aws iam create-role \
  --role-name iot-platform-api-role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --query Role.Arn \
  --output text)
```
```bash
aws iam attach-role-policy \
  --role-name iot-platform-api-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```bash
cat > lambda-dynamodb-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem"],
                 "Resource": ["arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/iot-data",
                              "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/house-data",
                              "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/room-data"]}]
}
EOF
```
```bash
aws iam put-role-policy \
  --role-name iot-platform-api-role \
  --policy-name read-write-iot-platform-tables \
  --policy-document file://lambda-dynamodb-policy.json
```

**Package the code** - one zip file for all three functions:
```bash
cd iot-lambda-api && zip ../iot-lambda-api.zip *.py && cd ..
```

**Create the three functions** from the same zip file. Each one gets its own handler (`device.lambda_handler`, ...) and the API key as an environment variable. If it fails with `The role defined for the function cannot be assumed by Lambda`, the new role isn't ready yet: wait 10 seconds and run the loop again (an already created function then reports `Function already exist` - that's fine):
```bash
for FUNCTION in device house rooms; do
  aws lambda create-function \
    --region $REGION \
    --function-name iot-platform-$FUNCTION \
    --runtime python3.13 \
    --handler $FUNCTION.lambda_handler \
    --role $LAMBDA_ROLE_ARN \
    --zip-file fileb://iot-lambda-api.zip \
    --environment "Variables={API_KEY=$API_KEY}"
done
```

**Option B: Using PowerShell**

**Download the function code:**
```powershell
mkdir iot-lambda-api
```
```powershell
foreach ($FILE in "common", "device", "house", "rooms") {
  curl -o "iot-lambda-api/$FILE.py" "https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/11-serverless-iot-platform/aws/iot-lambda-api/$FILE.py"
}
```

**Generate an API key** (32 random hexadecimal characters) and save it - you'll need it in every request:
```powershell
$API_KEY=$(openssl rand -hex 16)
```
```powershell
$API_KEY
```

**Create the execution role of the functions.** `AWSLambdaBasicExecutionRole` allows writing logs, and the inline policy allows reading and writing only the three tables:
```powershell
@'
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
'@ | Set-Content lambda-trust-policy.json
```
```powershell
$LAMBDA_ROLE_ARN=$(aws iam create-role `
  --role-name iot-platform-api-role `
  --assume-role-policy-document file://lambda-trust-policy.json `
  --query Role.Arn `
  --output text)
```
```powershell
aws iam attach-role-policy `
  --role-name iot-platform-api-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```powershell
@"
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem"],
                 "Resource": ["arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/iot-data",
                              "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/house-data",
                              "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/room-data"]}]
}
"@ | Set-Content lambda-dynamodb-policy.json
```
```powershell
aws iam put-role-policy `
  --role-name iot-platform-api-role `
  --policy-name read-write-iot-platform-tables `
  --policy-document file://lambda-dynamodb-policy.json
```

**Package the code** - one zip file for all three functions:
```powershell
cd iot-lambda-api; zip ../iot-lambda-api.zip *.py; cd ..
```

**Create the three functions** from the same zip file. Each one gets its own handler (`device.lambda_handler`, ...) and the API key as an environment variable. If it fails with `The role defined for the function cannot be assumed by Lambda`, the new role isn't ready yet: wait 10 seconds and run the loop again (an already created function then reports `Function already exist` - that's fine):
```powershell
foreach ($FUNCTION in "device", "house", "rooms") {
  aws lambda create-function `
    --region $REGION `
    --function-name "iot-platform-$FUNCTION" `
    --runtime python3.13 `
    --handler "$FUNCTION.lambda_handler" `
    --role $LAMBDA_ROLE_ARN `
    --zip-file fileb://iot-lambda-api.zip `
    --environment "Variables={API_KEY=$API_KEY}"
}
```

### Step 9: Create the HTTP API

An **HTTP API** in API Gateway receives HTTPS requests and passes them to the Lambda functions. Each **route** (a method and a path, for example `GET /api/device`) points to an **integration** (a Lambda function). The CORS configuration lets web pages from other addresses, such as the frontend, call the API.

**Option A: Using Bash (recommended)**

**Create the API** and save its ID:
```bash
API_ID=$(aws apigatewayv2 create-api \
  --region $REGION \
  --name iot-platform-api \
  --protocol-type HTTP \
  --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,OPTIONS,AllowHeaders=content-type" \
  --query ApiId \
  --output text)
```

**Connect each function to the API.** For every function the loop creates an integration, a `GET` and a `POST` route, and a permission that lets API Gateway call the function (only from this API and path):
```bash
for FUNCTION in device house rooms; do
  INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --region $REGION \
    --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri arn:aws:lambda:$REGION:$ACCOUNT_ID:function:iot-platform-$FUNCTION \
    --payload-format-version 2.0 \
    --query IntegrationId \
    --output text)
  aws apigatewayv2 create-route --region $REGION --api-id $API_ID --route-key "GET /api/$FUNCTION" --target integrations/$INTEGRATION_ID
  aws apigatewayv2 create-route --region $REGION --api-id $API_ID --route-key "POST /api/$FUNCTION" --target integrations/$INTEGRATION_ID
  aws lambda add-permission \
    --region $REGION \
    --function-name iot-platform-$FUNCTION \
    --statement-id allow-api-gateway \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*/api/$FUNCTION"
done
```

**Publish the API.** The `$default` stage serves the API at its base address, and `--auto-deploy` publishes every later change automatically:
```bash
aws apigatewayv2 create-stage --region $REGION --api-id $API_ID --stage-name '$default' --auto-deploy
```

**Important:** Save your API URL:
```bash
echo "Your API URL: https://$API_ID.execute-api.$REGION.amazonaws.com"
```

**Option B: Using PowerShell**

**Create the API** and save its ID:
```powershell
$API_ID=$(aws apigatewayv2 create-api `
  --region $REGION `
  --name iot-platform-api `
  --protocol-type HTTP `
  --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,OPTIONS,AllowHeaders=content-type" `
  --query ApiId `
  --output text)
```

**Connect each function to the API.** For every function the loop creates an integration, a `GET` and a `POST` route, and a permission that lets API Gateway call the function (only from this API and path):
```powershell
foreach ($FUNCTION in "device", "house", "rooms") {
  $INTEGRATION_ID=$(aws apigatewayv2 create-integration `
    --region $REGION `
    --api-id $API_ID `
    --integration-type AWS_PROXY `
    --integration-uri "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:iot-platform-$FUNCTION" `
    --payload-format-version 2.0 `
    --query IntegrationId `
    --output text)
  aws apigatewayv2 create-route --region $REGION --api-id $API_ID --route-key "GET /api/$FUNCTION" --target "integrations/$INTEGRATION_ID"
  aws apigatewayv2 create-route --region $REGION --api-id $API_ID --route-key "POST /api/$FUNCTION" --target "integrations/$INTEGRATION_ID"
  aws lambda add-permission `
    --region $REGION `
    --function-name "iot-platform-$FUNCTION" `
    --statement-id allow-api-gateway `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:$API_ID/*/*/api/$FUNCTION"
}
```

**Publish the API.** The `$default` stage serves the API at its base address, and `--auto-deploy` publishes every later change automatically:
```powershell
aws apigatewayv2 create-stage --region $REGION --api-id $API_ID --stage-name '$default' --auto-deploy
```

**Important:** Save your API URL:
```powershell
"Your API URL: https://$API_ID.execute-api.$REGION.amazonaws.com"
```

---

## Part 5: Test REST API with Postman

### Step 10: Test API Endpoints

Use the API URL from Step 9 and the API key from Step 8 (`echo $API_KEY` in Bash, `$API_KEY` in PowerShell). Open **Postman** and create the following requests, or use `curl` in CloudShell.

#### 1. GET Device Data (Query IoT Telemetry)

**Request:**
- Method: `GET`
- URL: `https://<api-id>.execute-api.<region>.amazonaws.com/api/device?device_id=my-iot-device-01&code=<your-api-key>`
- No body needed

With curl in CloudShell (Bash):
```bash
curl "https://$API_ID.execute-api.$REGION.amazonaws.com/api/device?device_id=my-iot-device-01&code=$API_KEY"
```

**Expected Response:**
- Status: `200 OK`
- Body: JSON array with the readings of your device, ordered by timestamp:
```json
[
 {
  "humidity": 48.14237517132358,
  "deviceid": "my-iot-device-01",
  "pressure": 1026.7868644459404,
  "temperature": 28.631555199512277,
  "timestamp": 1793814778.984089
 }
]
```

**If you get 404:** check that your device simulator is still running and that data is in the `iot-data` table (Step 6). **If you get 401:** the `code` is missing or wrong.

#### 2. POST Create House

**Request:**
- Method: `POST`
- URL: `https://<api-id>.execute-api.<region>.amazonaws.com/api/house?code=<your-api-key>`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "id": "house-001",
  "name": "My Smart Home",
  "location": "London, UK"
}
```

With curl in CloudShell (Bash):
```bash
curl -X POST -H "Content-Type: application/json" -d '{"id": "house-001", "name": "My Smart Home", "location": "London, UK"}' "https://$API_ID.execute-api.$REGION.amazonaws.com/api/house?code=$API_KEY"
```

**Expected Response:**
- Status: `201 Created`
- Body:
```json
{
 "message": "House entity created successfully"
}
```

Send the same request again: you get `409 Conflict`, because a house with this `id` already exists.

#### 3. GET House Data

**Request:**
- Method: `GET`
- URL: `https://<api-id>.execute-api.<region>.amazonaws.com/api/house?house_id=house-001&code=<your-api-key>`

**Expected Response:**
- Status: `200 OK`
- Body:
```json
[
 {
  "id": "house-001",
  "location": "London, UK",
  "houseid": "My Smart Home"
 }
]
```

#### 4. POST Create Room

**Request:**
- Method: `POST`
- URL: `https://<api-id>.execute-api.<region>.amazonaws.com/api/rooms?code=<your-api-key>`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "id": "room-001",
  "room_name": "Living Room",
  "house_id": "house-001",
  "location": "Ground Floor"
}
```

**Expected Response:**
- Status: `201 Created`
- Body:
```json
{
 "message": "Rooms entity created successfully"
}
```

#### 5. GET Room Data

**Request:**
- Method: `GET`
- URL: `https://<api-id>.execute-api.<region>.amazonaws.com/api/rooms?room_id=room-001&code=<your-api-key>`

**Expected Response:**
- Status: `200 OK`
- Body:
```json
[
 {
  "room_name": "Living Room",
  "location": "Ground Floor",
  "id": "room-001",
  "house_id": "house-001"
 }
]
```

**Congratulations!** You've successfully built and tested a complete serverless IoT platform with REST API endpoints.

### Step 11: Explore the Platform in the AWS Console

1. **AWS IoT Core** → **Message routing** → **Rules** → `iot_data_to_dynamodb`: the SQL query and the DynamoDB action
2. **Lambda** → **Functions** → `iot-platform-device` → **Monitor**: the number of requests, the duration and the errors; **View CloudWatch logs** shows the log of each request
3. **API Gateway** → `iot-platform-api` → **Routes**: the six routes and their integrations; **CORS**: the CORS configuration
4. **DynamoDB** → **Tables** → `house-data` and `room-data` → **Explore table items**: the items you created with POST requests

---

## Part 6: (Optional) Deploy Frontend

The Vue.js frontend in `example-frontend` shows the temperature of your device as a line chart. It works with the AWS API without code changes: it calls `<base URL>/api/device?device_id=...&code=<key>`, like the Azure version. You build it in CloudShell, which has Node.js and npm, and host it as an S3 static website, as in exercise 8.

The steps use **Bash** in **AWS CloudShell**. If you worked in PowerShell, type `exit` to go back to Bash, and set the variables again: `REGION="eu-west-2"`, `API_ID="<your-api-id>"` (the part before `.execute-api` in your API URL) and `API_KEY="<your-api-key>"`.

1. Download the repository and go to the frontend:
   ```bash
   git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
   ```
   ```bash
   cd course-iot-cloud-computing/11-serverless-iot-platform/example-frontend
   ```
2. Create the `.env` file with your API URL, API key and device ID. The variable is called `VITE_AZURE_FUNCTIONS_URL`, but it's just the base URL of the API:
   ```bash
   cat > .env <<EOF
   VITE_AZURE_FUNCTIONS_URL=https://$API_ID.execute-api.$REGION.amazonaws.com
   VITE_FUNCTION_KEY=$API_KEY
   VITE_DEVICE_ID=my-iot-device-01
   EOF
   ```
3. Install the dependencies and build the application (the result is in `dist`):
   ```bash
   npm install
   ```
   ```bash
   npm run build
   ```
4. Create a bucket for the website. The error document is also `index.html`, so addresses such as `/diagram/line` open the application too:
   ```bash
   BUCKET_NAME="iot-platform-frontend-$RANDOM$RANDOM"
   ```
   ```bash
   aws s3 mb s3://$BUCKET_NAME --region $REGION
   ```
   ```bash
   aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document index.html
   ```
   ```bash
   aws s3api put-public-access-block --bucket $BUCKET_NAME --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=false,RestrictPublicBuckets=false
   ```
   ```bash
   cat > policy.json << EOF
   {
     "Version": "2012-10-17",
     "Statement": [{"Sid": "PublicReadGetObject", "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::$BUCKET_NAME/*"}]
   }
   EOF
   ```
   ```bash
   aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://policy.json
   ```
5. Upload the application:
   ```bash
   aws s3 sync dist s3://$BUCKET_NAME
   ```
6. Open the website and click through to the line chart:
   ```bash
   echo "http://$BUCKET_NAME.s3-website.$REGION.amazonaws.com"
   ```

**Note:** the API key is built into the JavaScript of the website, so anyone who opens the page can find it. That's fine for this exercise, but a real application signs users in (for example with Amazon Cognito) instead.

---

## Troubleshooting

### No data in DynamoDB (iot-data table)
- **Check device simulator:** Ensure `simple_mqtt_device_simulator.py` is still running and says `Device sent message`
- **Check the messages:** In the MQTT test client of IoT Core, subscribe to `devices/#` - do messages arrive?
- **Check the rule:** In IoT Core → Message routing → Rules, the rule `iot_data_to_dynamodb` must be **Active**, and its query must use the topic `devices/+/messages/events/`
- **Check the role:** The role `iot-data-to-dynamodb-role` must allow `dynamodb:PutItem` on the `iot-data` table in the same region
- **See rule errors:** IoT Core doesn't log rule errors by default. You can add an error action to the rule or turn on logging in IoT Core → Settings (this creates CloudWatch logs)

### API returns 500 Internal Server Error
- **Check the function logs:** Lambda → your function → Monitor → View CloudWatch logs
- **Check the tables:** `iot-data`, `house-data` and `room-data` must exist in the same region as the functions
- **Check the role:** `iot-platform-api-role` must have the policy `read-write-iot-platform-tables`

### API returns 404 Not Found with `{"message":"Not Found"}`
- **Check the URL:** It must be `/api/device`, `/api/house` or `/api/rooms`, and the method must be GET or POST
- **Check the stage:** The `$default` stage must exist (Step 9)

### API returns 401
- **Check the key:** The URL must end with `&code=<your-api-key>` (or `?code=` if it's the only parameter), with the key from Step 8

### API returns `{"message":"Internal Server Error"}` for every request
- **Check the permission:** API Gateway can't call the function. Run the `add-permission` command of Step 9 again for the function

### Device simulator connection errors
- **Check the device ID:** It must be the same as the thing name, because the policy only allows this MQTT client ID
- **Check the endpoint:** Should be `<id>-ats.iot.<region>.amazonaws.com` from Step 1, in the same region as the policy
- **Check the files:** `device.pem.crt`, `private.pem.key` and `AmazonRootCA1.pem` must be next to the simulator
- **Check port number:** Should be `8883` for secure MQTT (MQTTS)

---

## Cleanup

**Important:** Delete all resources to avoid charges! Run these commands in **AWS CloudShell**, in the session where you set the variables. The commands are the same in Bash and PowerShell, except for the loops and the certificate ID.

**Delete the frontend bucket** (only if you did Part 6):
```bash
aws s3 rb s3://$BUCKET_NAME --force
```

**Delete the API:**
```bash
aws apigatewayv2 delete-api --region $REGION --api-id $API_ID
```

**Delete the functions and their logs** - Bash:
```bash
for FUNCTION in device house rooms; do
  aws lambda delete-function --region $REGION --function-name iot-platform-$FUNCTION
  aws logs delete-log-group --region $REGION --log-group-name /aws/lambda/iot-platform-$FUNCTION
done
```
PowerShell:
```powershell
foreach ($FUNCTION in "device", "house", "rooms") {
  aws lambda delete-function --region $REGION --function-name "iot-platform-$FUNCTION"
  aws logs delete-log-group --region $REGION --log-group-name "/aws/lambda/iot-platform-$FUNCTION"
}
```

**Delete the role of the functions:**
```bash
aws iam delete-role-policy --role-name iot-platform-api-role --policy-name read-write-iot-platform-tables
```
```bash
aws iam detach-role-policy --role-name iot-platform-api-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```bash
aws iam delete-role --role-name iot-platform-api-role
```

**Delete the IoT rule and its role:**
```bash
aws iot delete-topic-rule --region $REGION --rule-name iot_data_to_dynamodb
```
```bash
aws iam delete-role-policy --role-name iot-data-to-dynamodb-role --policy-name write-iot-data
```
```bash
aws iam delete-role --role-name iot-data-to-dynamodb-role
```

**Delete the tables:**
```bash
aws dynamodb delete-table --region $REGION --table-name iot-data
```
```bash
aws dynamodb delete-table --region $REGION --table-name house-data
```
```bash
aws dynamodb delete-table --region $REGION --table-name room-data
```

**Delete the IoT Core resources** (stop the device simulator first):

Save the certificate ID (the last part of the certificate's ARN) - Bash:
```bash
CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
```
PowerShell:
```powershell
$CERTIFICATE_ID=$CERTIFICATE_ARN.Split('/')[-1]
```

Detach the certificate from the thing and the policy from the certificate:
```bash
aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```
```bash
aws iot detach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
```

Deactivate and delete the certificate:
```bash
aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
```
```bash
aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
```

Delete the thing and the policy:
```bash
aws iot delete-thing --region $REGION --thing-name $THING_NAME
```
```bash
aws iot delete-policy --region $REGION --policy-name "$THING_NAME-policy"
```

---

## Summary and Learning Outcomes

Congratulations! You've built a complete serverless IoT platform. You learned:

✅ **AWS IoT Core**: Device connectivity with MQTT and X.509 certificates
✅ **IoT rules**: SQL-based message processing and routing, without a separate service
✅ **DynamoDB**: NoSQL tables with partition and sort keys
✅ **AWS Lambda**: Serverless functions, one per API endpoint
✅ **API Gateway**: An HTTP API with routes, Lambda integrations and CORS
✅ **IAM roles**: Least-privilege access between services, without keys in the code
✅ **End-to-end data flow**: Device → IoT Core → IoT rule → DynamoDB → Lambda → API

## Next Steps

- Change the rule's SQL query: send only readings with `temperature > 25` (`WHERE temperature > 25`), or add a second action
- Add DELETE endpoints (a `DELETE /api/house` route and `delete_item` in `house.py`)
- Replace the API key with a JWT authorizer of API Gateway and Amazon Cognito
- Turn on Time to Live in the `iot-data` table to delete old telemetry automatically (as in [exercise 9](../../9-storage-nosql/aws/readme.md))
- Use AWS IoT Rules to send an email (Amazon SNS) when the temperature is too high

---

## Reference Script

`aws-cli-iot-platform.sh` contains all the AWS CLI commands of this exercise. It's for reference only: following the steps above will help you understand each component better and troubleshoot any issues that arise.
