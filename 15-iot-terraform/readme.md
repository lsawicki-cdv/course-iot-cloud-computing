# Azure IoT Hub with Blob Storage - Terraform Deployment

> Using AWS instead? Follow the [AWS version of this exercise](aws/readme.md).

In this exercise, you'll use **Terraform** to deploy a complete IoT infrastructure with automatic message routing to Blob Storage. This is the Terraform equivalent of Exercise 13 (Bicep), so you can compare both Infrastructure as Code approaches. The IoT Hub, the storage account and the route live in a reusable Terraform **module**.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Architecture Overview

```
IoT Device (Python Simulator)
    ↓ (MQTT over TLS, Azure IoT SDK)
Azure IoT Hub (F1)
    ↓ (Message Routing - all messages by default)
Azure Blob Storage (telemetry as JSON files, one batch per minute)
```

The Terraform files:

```
15-iot-terraform/
  providers.tf  variables.tf  main.tf  outputs.tf     root configuration: resource group + module call
  modules/azure-iot-storage-route/                    IoT Hub, storage account, container, endpoint, route
  simple_azure_device_simulator.py                    the device simulator (as in Exercise 13)
```

### What You'll Learn

- How to deploy an IoT Hub with message routing to Blob Storage using Terraform
- How a Terraform module packages resources and how a root configuration calls it
- How one module input (`storage_level`) switches the route between "everything" and Exercise 13's filter
- Why Terraform state holds secrets
- Creating a device with the `az` CLI (Terraform has no resource for it) and verifying the data flow
- Comparing Terraform with Bicep for the same architecture

### Comparing with Exercise 13 (Bicep)

| Aspect | Exercise 13 (Bicep) | Exercise 15 (Terraform) |
|--------|---------------------|-------------------------|
| Configuration | 1 `main.bicep` file | 4 root `.tf` files + 1 module |
| Syntax | Bicep DSL | HCL (HashiCorp) |
| Resource names | Bicep `uniqueString` suffix | `random_string` suffix |
| State | Azure-managed (deployment history) | Local `terraform.tfstate` |
| Deploy command | `az deployment group create` | `terraform apply` |
| Message routing | Only `level="storage"` | Everything by default; `-var storage_level=storage` gives Exercise 13's filter |

## Tested Environments

- Ubuntu 24.04/26.04
- Terraform v1.11.0 and later, azurerm provider 4.x
- Python 3.10+
- Azure Cloud Shell (Bash)

## Prerequisites

- Azure account with active subscription
- Completed Exercise 14 (Terraform basics), see [Terraform Basics](../14-iaas-terraform/terraform-basics.md)
- Completed Exercise 13 (IoT Hub with Bicep) recommended for comparison

The IoT Hub uses the **F1 (free)** SKU, and a subscription can have only **one** F1 hub. Delete other free hubs (for example from Exercises 6 or 13) first, or see Troubleshooting.

---

## Part 1: Setup Terraform Environment

### Step 1: Open Azure Cloud Shell

1. Navigate to the **Azure Portal** (portal.azure.com)
2. Click the **Cloud Shell** icon (>_) in the top navigation bar
3. Use **Bash** (recommended) or **PowerShell** - the Terraform commands are the same in both

Verify Terraform:

```bash
terraform version
```

### Step 2: Get the Terraform Files

```bash
git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
cd course-iot-cloud-computing/15-iot-terraform
```

---

## Part 2: Understand the Terraform Configuration

Open the files with `code <file>` (the Cloud Shell editor) or `cat <file>`.

### Step 3: providers.tf

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}
```

- `azurerm` signs in with your Azure CLI login and uses the active subscription (`az account show`)
- `random` is used inside the module for the unique name suffix

### Step 4: main.tf (root) - a module call

The root `main.tf` creates the resource group and calls the module:

```hcl
module "iot_storage_route" {
  source = "./modules/azure-iot-storage-route"

  name_prefix         = var.name_prefix
  resource_group_name = azurerm_resource_group.iot_rg.name
  location            = azurerm_resource_group.iot_rg.location
  storage_level       = var.storage_level
}
```

A **module** is a directory of `.tf` files with its own inputs (`variable`) and outputs (`output`). The root passes values in, reads results out. The root variables (`variables.tf`) are `resource_group_name` (`iot-terraform-rg`), `location` (`uksouth`), `name_prefix` (`iot`) and `storage_level` (`null`).

### Step 5: The module resources

`modules/azure-iot-storage-route/main.tf` creates:

1. **random_string** - an 8-character suffix, so the globally unique names never collide (hub `iot-hub-<suffix>`, storage `iot<suffix>`). Nothing to edit when a name is taken.
2. **IoT Hub** (`azurerm_iothub`) - F1 free tier, 8,000 messages per day
3. **Storage account** - Standard LRS, no public blobs, TLS 1.2 minimum
4. **Blob container** (`azurerm_storage_container`) - `telemetrydata`, private
5. **Storage endpoint** (`azurerm_iothub_endpoint_storage_container`) - where the hub writes: JSON, a batch every 60 seconds, file name `{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}`
6. **Route** (`azurerm_iothub_route`) - which messages go to that endpoint

The module also checks `name_prefix` (lowercase letters and digits, starting with a letter, up to 11 characters) with a `validation` block, so a wrong value fails at plan time.

### Step 6: The route condition and `storage_level`

```hcl
condition = var.storage_level == null ? "true" : "level=\"${var.storage_level}\""
```

- By default (`storage_level` is `null`) the condition is `true`: **every** message goes to storage
- With `-var storage_level=storage` the condition is `level="storage"`: only messages with the custom property `level` equal to `storage`, exactly as in Exercise 13. You try this in Part 6.

### Step 7: outputs.tf

The root returns `resource_group_name`, `iot_hub_name`, `storage_account_name` and `blob_container_name` (the module's outputs passed through). The next steps read them with `terraform output`.

**Terraform state holds secrets.** The storage endpoint uses the storage account connection string, so `terraform.tfstate` contains the **storage account key**. It stays local and is gitignored (`*tfstate*`) - never commit it or paste it anywhere. The readme's blob commands use this key (`--auth-mode key`), which is a teaching shortcut: as the subscription Owner you can read the key anyway.

---

## Part 3: Deploy Infrastructure with Terraform

### Step 8: Initialize

```bash
terraform init -upgrade
```

This downloads the providers and initializes the module.

### Step 9: Review the Execution Plan

```bash
terraform plan -out main.tfplan
```

You should see `Plan: 7 to add, 0 to change, 0 to destroy.`: the resource group, the random suffix, the IoT Hub, the storage account, the container, the endpoint and the route. To use another region, add `-var location=<region>`.

### Step 10: Apply

```bash
terraform apply main.tfplan
```

Wait 3-4 minutes. At the end you'll see the outputs:

```
Outputs:

blob_container_name = "telemetrydata"
iot_hub_name = "iot-hub-k3x9a2bq"
resource_group_name = "iot-terraform-rg"
storage_account_name = "iotk3x9a2bq"
```

---

## Part 4: Create Device and Run the Simulator

Terraform's `azurerm` provider has no resource for a device identity, so you create it with the `az` CLI.

### Step 11: Create the IoT Device

**Option A: Bash (recommended)**

```bash
IOT_HUB_NAME=$(terraform output -raw iot_hub_name)
DEVICE_ID="terraform-device-01"

az iot hub device-identity create \
  --hub-name $IOT_HUB_NAME \
  --device-id $DEVICE_ID

az iot hub device-identity connection-string show \
  --hub-name $IOT_HUB_NAME \
  --device-id $DEVICE_ID \
  --output tsv
```

**Option B: PowerShell**

```powershell
$IOT_HUB_NAME=$(terraform output -raw iot_hub_name)
$DEVICE_ID="terraform-device-01"

az iot hub device-identity create `
  --hub-name $IOT_HUB_NAME `
  --device-id $DEVICE_ID

az iot hub device-identity connection-string show `
  --hub-name $IOT_HUB_NAME `
  --device-id $DEVICE_ID `
  --output tsv
```

Copy the **device connection string** (`HostName=...;DeviceId=...;SharedAccessKey=...`). It is a secret: don't commit it.

### Step 12: Configure the Simulator

`simple_azure_device_simulator.py` is the same simulator as in Exercise 13: it sends temperature, humidity and pressure every 10 seconds, with the custom property `level="storage"`. Open it (`code simple_azure_device_simulator.py`) and on line 9 replace

```python
conn_str = "connection_string"
```

with your device connection string.

### Step 13: Run the Simulator

**Option A: Bash (recommended)**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python simple_azure_device_simulator.py
```

**Option B: PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python simple_azure_device_simulator.py
```

(In Cloud Shell PowerShell use `python3 -m venv .venv` and `.venv/bin/Activate.ps1`.) You should see `Connected to Azure IoT` and a `Message sent: ...` line every 10 seconds. **Keep it running for at least 2 minutes** (the hub writes one batch per minute), then stop it with `Ctrl+C`.

---

## Part 5: Verify Data Flow to Blob Storage

Wait one more minute after stopping the simulator. In a second terminal (or after stopping the simulator), from the `15-iot-terraform` directory:

**Option A: Bash (recommended)**

```bash
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
CONTAINER=$(terraform output -raw blob_container_name)

az storage blob list \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER \
  --auth-mode key \
  --output table

BLOB_NAME=$(az storage blob list \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER \
  --auth-mode key \
  --query "[0].name" -o tsv)

az storage blob download \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER \
  --name "$BLOB_NAME" \
  --file telemetry-data.json \
  --auth-mode key

cat telemetry-data.json
```

**Option B: PowerShell**

```powershell
$STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
$CONTAINER=$(terraform output -raw blob_container_name)

az storage blob list `
  --account-name $STORAGE_ACCOUNT `
  --container-name $CONTAINER `
  --auth-mode key `
  --output table

$BLOB_NAME=$(az storage blob list `
  --account-name $STORAGE_ACCOUNT `
  --container-name $CONTAINER `
  --auth-mode key `
  --query "[0].name" -o tsv)

az storage blob download `
  --account-name $STORAGE_ACCOUNT `
  --container-name $CONTAINER `
  --name "$BLOB_NAME" `
  --file telemetry-data.json `
  --auth-mode key

Get-Content telemetry-data.json
```

You can also browse the container in the Azure Portal (storage account → **Storage browser** → **Blob containers** → `telemetrydata`). Each file holds one JSON object per message, one per line:

```json
{"EnqueuedTimeUtc":"2026-11-18T16:47:50Z","Properties":{"level":"storage"},"SystemProperties":{"connectionDeviceId":"terraform-device-01",...},"Body":{"temperature": 29.27, "humidity": 40.71, "pressure": 1069.17}}
```

`Body` is the payload of the simulator. The endpoint writes the whole IoT Hub message, so you also see the device ID and the custom properties (`level`).

---

## Part 6: Experiment with the Route Filter

Switch the route to Exercise 13's behavior by changing one module input.

### Step 14: Filter on `level="storage"`

First count the blobs now (wait 2 minutes after stopping the simulator, so the last batch is written):

**Option A: Bash (recommended)**

```bash
az storage blob list --account-name $STORAGE_ACCOUNT --container-name $CONTAINER \
  --auth-mode key --query "length(@)"
```

**Option B: PowerShell**

```powershell
az storage blob list --account-name $STORAGE_ACCOUNT --container-name $CONTAINER `
  --auth-mode key --query "length(@)"
```

Apply with the filter (an in-place update of the route):

```bash
terraform apply -var storage_level=storage
```

Review the plan (`condition: "true" -> "level=\"storage\""`) and type `yes`. Now open `simple_azure_device_simulator.py` and comment out the property line:

```python
# message.custom_properties["level"] = "storage"
```

Run the simulator again for 2 minutes, stop it, wait 2 more minutes and count the blobs again with the command above. The number is **unchanged**: the messages have no `level` property, so they no longer match the route (they go to the hub's built-in endpoint instead, see Exercise 13).

### Step 15: Restore

Remove the `#` from the property line, and switch the route back to everything:

```bash
terraform apply
```

(Without `-var`, `storage_level` is `null` again.) Run the simulator once more if you want to see new blobs.

---

## Part 7: Terraform vs Bicep

**Terraform (Exercise 15):**
- **Pros**: Multi-cloud, mature ecosystem, reusable modules, explicit plan before every change
- **Cons**: More files, state to manage (and protect), providers to install

**Bicep (Exercise 13):**
- **Pros**: Azure-native, one file, no state file to manage, new Azure features immediately
- **Cons**: Azure-only

**Resource declaration comparison:**

```hcl
# Terraform
resource "azurerm_iothub" "iothub" {
  name                = "${var.name_prefix}-hub-${random_string.suffix.result}"
  resource_group_name = var.resource_group_name
  location            = var.location

  sku {
    name     = "F1"
    capacity = 1
  }
}
```

```bicep
// Bicep (Exercise 13)
resource IoTHub 'Microsoft.Devices/IotHubs@2023-06-30' = {
  name: iotHubName
  location: location
  sku: {
    name: skuName
    capacity: skuUnits
  }
}
```

1. **Syntax**: Bicep uses `:` for properties, Terraform uses `=` and nested blocks
2. **API version**: Bicep states it, the Terraform provider hides it
3. **Reuse**: Terraform modules (this exercise) vs Bicep modules/parameters
4. **State**: `terraform.tfstate` (with secrets) vs deployment history kept by Azure

**Use Terraform when** you work with more than one cloud or your team already uses it. **Use Bicep when** you deploy only to Azure and want the simplest setup.

---

## Troubleshooting

The common Terraform problems are in [Common Troubleshooting](../14-iaas-terraform/terraform-basics.md#common-troubleshooting). Exercise specific ones:

### Apply fails because an F1 IoT Hub already exists

- A subscription can have only one free hub. Delete the other one (`az iot hub list --output table`, then `az iot hub delete --name <hub> --resource-group <rg>`) or destroy that exercise first

### Plan or apply fails with "subscription ID could not be determined"

- **Sign in**: Run `az login` (not needed in Cloud Shell) and check `az account show`
- **Pick the subscription**: Run `az account set --subscription <id>`, or `export ARM_SUBSCRIPTION_ID=<id>` (Bash) / `$env:ARM_SUBSCRIPTION_ID="<id>"` (PowerShell)

### Plan fails with "name_prefix must start with a lowercase letter..."

- Use only lowercase letters and digits, start with a letter, at most 11 characters: `terraform plan -var name_prefix=myiot -out main.tfplan`

### Plan fails with "undeclared variable" (`storage_account_name`, `iot_hub_name`)

- Those variables of the older version of this exercise no longer exist: names are unique by themselves now. Remove the `-var`

### No data in Blob Storage

- **Wait longer**: Batching is 60 seconds, plus processing time
- **Check the simulator**: It must print `Connected to Azure IoT` and `Message sent`; check that you used the **device** connection string
- **Check the route**: Azure Portal → IoT Hub → Message routing; the route must be enabled. With `storage_level` set, messages need the `level` property
- **Free tier limit**: F1 accepts 8,000 messages per day

### I deployed an older version of this exercise

- Applying the new files over an old deployment would delete and recreate the hub and storage account. Run `terraform destroy` with the **old** files first, then start again from Step 2

---

## Cleanup

**Important:** Delete all resources (this also deletes the stored telemetry and frees the F1 hub).

**Option A: Bash (recommended)**

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
az group exists --name iot-terraform-rg
```

**Option B: PowerShell**

```powershell
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
az group exists --name iot-terraform-rg
```

Wait 2-3 minutes. The last command should print `false`. Also delete the downloaded `telemetry-data.json`.

## Optional Next Steps

- Add a second route (Event Hub or Service Bus endpoint)
- Move the state to an Azure Storage Account (remote state)
- Create workspaces for dev/staging/prod

## Additional Resources

- [Terraform azurerm_iothub](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/iothub)
- [Terraform modules](https://developer.hashicorp.com/terraform/language/modules)
- [Azure IoT Hub message routing](https://learn.microsoft.com/azure/iot-hub/iot-hub-devguide-messages-d2c)
