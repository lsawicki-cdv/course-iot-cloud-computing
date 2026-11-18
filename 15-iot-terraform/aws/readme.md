# AWS IoT Core with Amazon S3 - Terraform Deployment

This is the AWS version of the [Azure Terraform IoT exercise](../readme.md). You'll use **Terraform** to deploy a complete IoT pipeline on AWS: an IoT rule that stores device messages in an S3 bucket, and the device itself (thing, certificate and policy). This is the Terraform equivalent of the CloudFormation template of [Exercise 13 on AWS](../../13-iac-iot-routing/aws/readme.md), so you can compare both Infrastructure as Code approaches. The rule and the device live in reusable Terraform **modules**.

| Azure | AWS |
|-------|-----|
| `azurerm` provider | `aws` provider |
| Resource group | No direct equivalent - Terraform's state lists everything it created |
| IoT Hub (F1) | AWS IoT Core - no hub to create: every account has one endpoint per region (`iot_endpoint` output) |
| Module `azure-iot-storage-route` | Module `aws-iot-storage-route` |
| Storage account + blob container | S3 bucket (private, encrypted, HTTPS only) |
| Storage endpoint (one blob per 60 seconds) | S3 rule action (one object per message) |
| Route (`condition = "true"` or `level="storage"`) | IoT rule (SQL without `WHERE`, or `WHERE get(get_user_properties('level'), 0) = 'storage'`) |
| Device identity created with `az iot hub device-identity create` | Module `aws-iot-device`: thing + X.509 certificate + IoT policy, all in Terraform |
| Device connection string (SAS token) | Certificate and private key files written by Terraform |
| Azure IoT Device SDK (`azure-iot-device`) | Paho MQTT client (`paho-mqtt`) with MQTT 5 |
| `random_string` suffix | S3 `bucket_prefix` (AWS adds the suffix) |
| Azure Cloud Shell (Terraform pre-installed) | AWS CloudShell (install Terraform yourself) |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. If your account is limited to one region (for example by your organization or a new AWS account with a selected Region), use that region instead (`-var region=<region>`, see Step 10 and Troubleshooting). AWS IoT Core and Amazon S3 are Free Tier eligible: on accounts created before July 2025 the Free Tier covers 500,000 IoT messages and 2,000 S3 PUT requests per month for 12 months, on newer accounts the costs are paid from your Free Tier credits. The simulator sends one message every 10 seconds, so one hour of running costs a fraction of a cent. Destroy everything at the end of the exercise.

## Architecture Overview

```
IoT Device (Python Simulator)
    ↓ (MQTT 5 over TLS, X.509 certificate)
AWS IoT Core
    ↓ (IoT rule - all messages by default)
Amazon S3 (telemetry as JSON files, one object per message)
```

The Terraform files:

```
15-iot-terraform/
  aws/
    providers.tf  variables.tf  main.tf  outputs.tf   root configuration: two module calls + endpoint lookup
    simple_aws_device_simulator.py                    the device simulator (as in Exercise 13 on AWS)
    AmazonRootCA1.pem                                 the Amazon root certificate the device trusts
  modules/aws-iot-storage-route/                      S3 bucket, IAM role, IoT rule
  modules/aws-iot-device/                             thing, certificate, IoT policy, certificate and key files
```

### What You'll Learn

- How to deploy an IoT rule with an S3 action using Terraform
- How a Terraform module packages resources and how a root configuration calls it
- How one module input (`storage_level`) switches the rule between "everything" and Exercise 13's filter
- How Terraform creates the device (thing, certificate, policy) - the part that is a CLI step on Azure
- Why Terraform state holds secrets
- Comparing Terraform with CloudFormation for the same architecture

### Comparing with Exercise 13 (CloudFormation)

| Aspect | Exercise 13 (CloudFormation) | Exercise 15 (Terraform) |
|--------|------------------------------|-------------------------|
| Configuration | 1 `template.yaml` | 4 root `.tf` files + 2 modules |
| Device | Created with `aws iot` CLI commands | `aws-iot-device` module |
| State | The stack | Local `terraform.tfstate` |
| Deploy command | `aws cloudformation deploy` | `terraform apply` |
| Message routing | Only `level = storage` | Everything by default; `-var storage_level=storage` gives Exercise 13's filter |

## Tested Environments

- AWS CloudShell (Bash)
- Ubuntu 24.04/26.04, Terraform v1.11.0 and later (Step 1 installs v1.16.1), aws provider 6.x
- Python 3.10+ (`paho-mqtt` 1.6.1)

## Prerequisites

- An AWS account (see [`1-cloud-account/aws`](../../1-cloud-account/aws/readme.md))
- Completed Exercise 14 (Terraform basics), see [Terraform Basics](../../14-iaas-terraform/terraform-basics.md)
- Completed the [AWS version of Exercise 13](../../13-iac-iot-routing/aws/readme.md) recommended for comparison

---

## Part 1: Setup Terraform Environment

### Step 1: Open AWS CloudShell and Install Terraform

1. Open the **AWS Console** in the region you want to use
2. Click the **CloudShell** icon (>_) in the top navigation bar
3. Use **Bash** (recommended) or **PowerShell** (`pwsh`) - the Terraform commands are the same in both

AWS CloudShell is already authenticated with your AWS account, but Terraform isn't pre-installed. **Install it into your home directory** (it stays there between CloudShell sessions):

```bash
curl -o terraform.zip https://releases.hashicorp.com/terraform/1.16.1/terraform_1.16.1_linux_amd64.zip
mkdir -p ~/bin
unzip -o terraform.zip terraform -d ~/bin
rm terraform.zip
```

Verify the installation:

```bash
terraform version
```

You should see `Terraform v1.16.1`. If you get `command not found`, add the directory to your path: `export PATH=$HOME/bin:$PATH` (Bash) or `$env:PATH="$HOME/bin:$env:PATH"` (PowerShell).

### Step 2: Get the Terraform Files

```bash
git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
cd course-iot-cloud-computing/15-iot-terraform/aws
```

The configuration uses the modules one directory up (`../modules`), so keep the directory structure of the repository.

---

## Part 2: Understand the Terraform Configuration

Open the files with `nano <file>` or `cat <file>`.

### Step 3: providers.tf

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>6.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~>2.5"
    }
  }
}

provider "aws" {
  region = var.region
}
```

- `aws` signs in with the credentials of CloudShell (or of the AWS CLI on your computer); the region comes from the variable `region` (`eu-west-2`)
- `local` writes the certificate and the private key of the device to files, inside the `aws-iot-device` module

### Step 4: main.tf (root) - module calls

```hcl
module "storage_route" {
  source = "../modules/aws-iot-storage-route"

  name_prefix   = var.name_prefix
  storage_level = var.storage_level
}

module "device" {
  source = "../modules/aws-iot-device"

  thing_name = var.device_id
  output_dir = path.module
}

# The endpoint the simulator connects to
data "aws_iot_endpoint" "endpoint" {
  endpoint_type = "iot:Data-ATS"
}
```

A **module** is a directory of `.tf` files with its own inputs (`variable`) and outputs (`output`). The root passes values in and reads results out. The root variables (`variables.tf`) are `region` (`eu-west-2`), `name_prefix` (`iot`), `device_id` (`terraform-device-01`) and `storage_level` (`null`). The `data` block only reads the IoT Core endpoint of your account and region - it creates nothing.

### Step 5: The storage route module

`modules/aws-iot-storage-route/main.tf` creates:

1. **S3 bucket** (`aws_s3_bucket`) - the name is `<name_prefix>-telemetry-` plus a suffix added by AWS, so it never collides. `force_destroy = true` lets `terraform destroy` delete the stored telemetry too
2. **Public access block, encryption and bucket policy** - the bucket is private, encrypted and accepts only HTTPS requests
3. **IAM role** (`aws_iam_role`) - the role that AWS IoT assumes (only from your account); it may do only `s3:PutObject` on this bucket
4. **IoT rule** (`aws_iot_topic_rule`) - the counterpart of the IoT Hub route, with an S3 action

The module also checks `name_prefix` (lowercase letters and digits, starting with a letter, up to 11 characters) with a `validation` block, so a wrong value fails at plan time.

### Step 6: The rule SQL and `storage_level`

```hcl
sql = join(" ", compact([
  "SELECT *, topic(2) AS device_id, timestamp() AS received_at FROM 'devices/+/messages/events/'",
  var.storage_level == null ? "" : "WHERE get(get_user_properties('level'), 0) = '${var.storage_level}'",
]))
```

- By default (`storage_level` is `null`) there is no `WHERE`: **every** message on the topic goes to S3
- With `-var storage_level=storage` the rule adds `WHERE get(get_user_properties('level'), 0) = 'storage'`: only messages with the MQTT 5 user property `level` equal to `storage`, exactly as in Exercise 13. You try this in Part 6.

The S3 action writes each message under the key `<device_id>/<yyyy>/<MM>/<dd>/<HH>/<mm>/<uuid>.json`.

### Step 7: The device module

`modules/aws-iot-device/main.tf` creates what you did with CLI commands in Exercise 13:

1. **Certificate** (`aws_iot_certificate`) - IoT Core creates the key pair and signs the certificate; `active = true`
2. **Thing** (`aws_iot_thing`) - named `terraform-device-01` (the `device_id` variable)
3. **IoT policy** (`aws_iot_policy`) - the device may connect only with the client ID equal to its thing name, and publish only to `devices/<thing name>/messages/events/`
4. **Attachments** - the policy and the thing are attached to the certificate
5. **Files** (`local_sensitive_file`) - `device.pem.crt` and `private.pem.key` written next to the simulator, with permissions `0600`

The simulator's `device_id` must equal the thing name (both are `terraform-device-01`), because the policy allows only that client ID.

### Step 8: outputs.tf

The root returns `bucket_name`, `rule_name`, `iot_endpoint` and `device_id`. The next steps read them with `terraform output`.

**Terraform state holds secrets.** `terraform.tfstate` contains the **private key** of the device (and the same key is in `private.pem.key`). The state and the key files stay local and are gitignored (`*tfstate*`, `*.pem.key`, `*.pem.crt`) - never commit them or paste them anywhere. Anyone with the private key can connect as your device.

---

## Part 3: Deploy Infrastructure with Terraform

### Step 9: Initialize

```bash
terraform init -upgrade
```

This downloads the providers and initializes the modules.

### Step 10: Review the Execution Plan

```bash
terraform plan -out main.tfplan
```

You should see `Plan: 14 to add, 0 to change, 0 to destroy.`: the bucket with its 3 settings, the role with its policy, the rule, and the thing, certificate, policy, 2 attachments and 2 files of the device. If you use another region than `eu-west-2`, add `-var region=<region>` to **every** `plan` (also to `plan -destroy` in the cleanup).

### Step 11: Apply

```bash
terraform apply main.tfplan
```

Wait about 30 seconds. At the end you'll see the outputs:

```
Outputs:

bucket_name = "iot-telemetry-20261118123456789000000001"
device_id = "terraform-device-01"
iot_endpoint = "a1b2c3d4e5f6g7-ats.iot.eu-west-2.amazonaws.com"
rule_name = "iot_storage_route"
```

---

## Part 4: Run the Simulator

### Step 12: Configure the Simulator

`simple_aws_device_simulator.py` is the same simulator as in Exercise 13 on AWS: it sends temperature, humidity and pressure every 10 seconds over MQTT 5, with the user property `level="storage"`. Terraform already put the certificate and the key next to it. Print your endpoint:

```bash
terraform output -raw iot_endpoint
```

Open the simulator (`nano simple_aws_device_simulator.py`) and on line 15 replace

```python
iot_endpoint = "iot_endpoint"
```

with your endpoint (keep the quotes). `device_id` on line 14 is already `terraform-device-01`.

### Step 13: Run the Simulator

**Option A: Bash (recommended)**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python simple_aws_device_simulator.py
```

**Option B: PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python simple_aws_device_simulator.py
```

(In CloudShell PowerShell use `python3 -m venv .venv` and `.venv/bin/Activate.ps1`.) You should see `Connected to AWS IoT with result code: Success` and a `Message sent: ...` line every 10 seconds. **Keep it running for at least 1 minute**, then stop it with `Ctrl+C`.

---

## Part 5: Verify Data Flow to S3

Unlike IoT Hub, which writes one blob per batch, the rule writes **each message as a separate object right away**. From the `15-iot-terraform/aws` directory (use your region instead of `eu-west-2` if you changed it):

**Option A: Bash (recommended)**

```bash
REGION=eu-west-2
BUCKET_NAME=$(terraform output -raw bucket_name)

aws s3 ls s3://$BUCKET_NAME --recursive --region $REGION

OBJECT_KEY=$(aws s3api list-objects-v2 \
  --bucket $BUCKET_NAME \
  --region $REGION \
  --query "Contents[0].Key" \
  --output text)

aws s3 cp s3://$BUCKET_NAME/$OBJECT_KEY downloaded-telemetry.json --region $REGION

cat downloaded-telemetry.json
```

**Option B: PowerShell**

```powershell
$REGION="eu-west-2"
$BUCKET_NAME=$(terraform output -raw bucket_name)

aws s3 ls s3://$BUCKET_NAME --recursive --region $REGION

$OBJECT_KEY=$(aws s3api list-objects-v2 `
  --bucket $BUCKET_NAME `
  --region $REGION `
  --query "Contents[0].Key" `
  --output text)

aws s3 cp "s3://$BUCKET_NAME/$OBJECT_KEY" downloaded-telemetry.json --region $REGION

Get-Content downloaded-telemetry.json
```

You can also browse the bucket in the AWS Console (**S3** → your bucket → `terraform-device-01/YYYY/MM/DD/HH/mm/`). Each file holds one message:

```json
{"temperature":25.332355650533767,"humidity":49.988567938773855,"pressure":1073.9131653399668,"device_id":"terraform-device-01","received_at":1794935509264}
```

It is the body sent by the device plus the two fields added by the rule SQL (`device_id` from the topic, `received_at` in milliseconds since 1970). IoT Hub instead wraps every message in an envelope with `Properties`, `SystemProperties` and `Body`.

---

## Part 6: Experiment with the Rule Filter

Switch the rule to Exercise 13's behavior by changing one module input.

### Step 14: Filter on `level="storage"`

First count the objects now:

**Option A: Bash (recommended)**

```bash
aws s3api list-objects-v2 --bucket $BUCKET_NAME --region $REGION --query "length(Contents)"
```

**Option B: PowerShell**

```powershell
aws s3api list-objects-v2 --bucket $BUCKET_NAME --region $REGION --query "length(Contents)"
```

Apply with the filter (an in-place update of the rule; add `-var region=<region>` if you use another region):

```bash
terraform apply -var storage_level=storage
```

Review the plan (the `sql` of the rule changes) and type `yes`. Now open `simple_aws_device_simulator.py` and comment out the property line (line 62):

```python
# properties.UserProperty = ("level", "storage")
```

Run the simulator again for 1 minute and stop it. Count the objects again with the command above. The number is **unchanged**: the messages have no `level` property, so the rule no longer selects them (they only reach MQTT subscribers, e.g. the MQTT test client - see Exercise 13).

### Step 15: Restore

Remove the `#` from the property line, and switch the rule back to everything:

```bash
terraform apply
```

(Without `-var`, `storage_level` is `null` again; keep `-var region=<region>` if you use it.) Run the simulator once more if you want to see new objects.

---

## Part 7: Terraform vs CloudFormation

**Terraform (Exercise 15):**
- **Pros**: Multi-cloud, reusable modules (the same module style as the Azure version), explicit plan before every change, can write local files (the device certificate)
- **Cons**: More files, a tool to install in CloudShell, state to manage (and protect)

**CloudFormation (Exercise 13):**
- **Pros**: AWS-native, one file, no state file to manage, automatic rollback, nothing to install
- **Cons**: AWS-only; cannot create the certificate files, so the device needs CLI steps

**Resource declaration comparison:**

```hcl
# Terraform
resource "aws_iot_topic_rule" "storage_route" {
  name        = "${var.name_prefix}_storage_route"
  enabled     = true
  sql_version = "2016-03-23"
  sql         = "SELECT * FROM 'devices/+/messages/events/'"
  ...
}
```

```yaml
# CloudFormation (Exercise 13)
StorageRoute:
  Type: AWS::IoT::TopicRule
  Properties:
    RuleName: !Sub ${ProjectName}_storage_route
    TopicRulePayload:
      Sql: SELECT * FROM 'devices/+/messages/events/'
      ...
```

**Use Terraform when** you work with more than one cloud or your team already uses it. **Use CloudFormation when** you deploy only to AWS and want the simplest setup.

---

## Troubleshooting

The common Terraform problems are in [Common Troubleshooting](../../14-iaas-terraform/terraform-basics.md#common-troubleshooting). Exercise specific ones:

### Plan fails with "name_prefix must start with a lowercase letter..."

- Use only lowercase letters and digits, start with a letter, at most 11 characters: `terraform plan -var name_prefix=myiot -out main.tfplan`

### Plan or apply fails with "AccessDenied" or "not authorized" (for example on `iot:DescribeEndpoint`)

- **Your account may be limited to some regions** (for example by a policy of your organization): Use an allowed region with `-var region=<region>` in **every** `plan`, `apply` and `plan -destroy`, for example `terraform plan -var region=eu-north-1 -out main.tfplan`. Use the same region in the `--region` of the `aws s3` commands

### `terraform: command not found` after reopening CloudShell

- **Add the install directory to your path**: `export PATH=$HOME/bin:$PATH` (Bash) or `$env:PATH="$HOME/bin:$env:PATH"` (PowerShell). If `~/bin/terraform` is gone, repeat Step 1

### No objects in S3

- **Check the endpoint**: `iot_endpoint` in the simulator must be the output of `terraform output -raw iot_endpoint` (from the same region as the deployment)
- **Check the device ID**: `device_id` in the simulator must equal the `device_id` output - the IoT policy allows only that client ID and its topic, so the connection (or the publish) is refused otherwise
- **Check the certificate files**: `device.pem.crt`, `private.pem.key` and `AmazonRootCA1.pem` must be in the folder you run the simulator from (Terraform writes the first two there)
- **Check the user property**: With `storage_level` set, messages need `properties.UserProperty = ("level", "storage")`, and the client must use `mqtt.MQTTv5`
- **Check the metrics**: CloudWatch → **Metrics** → **IoT** → `RuleName` = `iot_storage_route`: `TopicMatch` shows messages that arrive on the topic, `Success` / `Failure` of the `S3` action show the stored messages and the failed writes
- **Network issues**: Ensure your firewall allows outbound traffic on port 8883

### Simulator prints a connection error

- **Check the endpoint and the region**: A wrong `iot_endpoint` gives a name resolution or timeout error
- **The certificate is gone**: After `terraform destroy` and a new `apply` the certificate is new - use the new files and run the simulator from this directory

---

## Cleanup

**Important:** Stop the simulator (`Ctrl+C`) and delete all resources. `terraform destroy` deletes the objects in the bucket too (`force_destroy`), the certificate and `device.pem.crt` / `private.pem.key`.

**Option A: Bash (recommended)**

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```

**Option B: PowerShell**

```powershell
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```

(Add `-var region=<region>` to the `plan` if you used another region.) Wait about 30 seconds. Verify - the three lists must be empty and the last command must not list your bucket:

**Option A: Bash (recommended)**

```bash
aws iot list-things --region $REGION --query "things[].thingName"
aws iot list-topic-rules --region $REGION --query "rules[].ruleName"
aws iot list-certificates --region $REGION --query "certificates[].certificateId"
aws s3 ls | grep telemetry
```

**Option B: PowerShell**

```powershell
aws iot list-things --region $REGION --query "things[].thingName"
aws iot list-topic-rules --region $REGION --query "rules[].ruleName"
aws iot list-certificates --region $REGION --query "certificates[].certificateId"
aws s3 ls | Select-String telemetry
```

(If you listed other things, rules or certificates in your account, only those of this exercise must be gone.) Also delete the downloaded `downloaded-telemetry.json` and the `terraform.tfstate` files when you no longer need them: the state holds the device's private key, and it must never be committed.

## Optional Next Steps

- Add a second device with another `module "device"` block (a different `thing_name` and `output_dir`, so its certificate and key don't overwrite the first device's files)
- Add an error action to the rule (CloudWatch Logs) to see failed writes
- Store Terraform state remotely in an S3 bucket (`backend "s3"`)
- Compare with the [Azure version](../readme.md): same workflow and module style, different resources

## Additional Resources

- [Terraform aws_iot_topic_rule](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iot_topic_rule)
- [Terraform modules](https://developer.hashicorp.com/terraform/language/modules)
- [AWS IoT rules](https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html)
