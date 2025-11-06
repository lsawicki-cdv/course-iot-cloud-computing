# Azure IoT Hub with Blob Storage - Terraform Deployment

In this exercise, you'll use **Terraform** to deploy a complete IoT infrastructure with automatic message routing to Blob Storage. This is the Terraform equivalent of Exercise 13 (Bicep), allowing you to compare both Infrastructure as Code approaches.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Why This Exercise Matters

This exercise demonstrates the same IoT architecture as Exercise 13, but using **Terraform** instead of **Bicep**. This hands-on comparison helps you understand:
- How the same infrastructure looks in different IaC tools
- The strengths and weaknesses of each approach
- When to choose Terraform vs Bicep for your projects

## Architecture Overview

This Terraform configuration deploys a complete IoT data pipeline:

```
IoT Device (Python Simulator)
    ↓ (HTTPS with Azure IoT SDK)
Azure IoT Hub
    ↓ (Message Routing - routes ALL messages)
Azure Blob Storage (stores telemetry as JSON files)
```

### What You'll Learn

- How to deploy IoT Hub infrastructure using Terraform
- Terraform resource blocks for Azure IoT services
- Automatic message routing configuration with Terraform
- Azure IoT Hub endpoint and route resources
- Comparing Terraform vs Bicep for the same architecture
- Device connection string authentication
- Verifying data flow to Blob Storage

### Comparing with Exercise 13 (Bicep)

| Aspect | Exercise 13 (Bicep) | Exercise 15 (Terraform) |
|--------|---------------------|-------------------------|
| Configuration Files | 1 main.bicep file | 4 separate .tf files |
| Syntax | Bicep DSL | HCL (HashiCorp) |
| Resource Names | Bicep-specific | Terraform provider names |
| State Management | Azure-managed | Local terraform.tfstate |
| Deployment Command | `az deployment group create` | `terraform apply` |
| Message Routing | Condition-based (`level="storage"`) | Routes all messages (`true`) |

## Tested Environments

- Ubuntu 22.04/24.04
- Terraform v1.11.0
- Python 3.10.12+
- Azure Cloud Shell (Bash)

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- Completed Exercise 14 (Terraform basics)
- Completed Exercise 13 (IoT Hub with Bicep) recommended for comparison
- Basic understanding of IoT Hub concepts

---

## Part 1: Setup Terraform Environment

### Step 1: Open Azure Cloud Shell

1. Navigate to the **Azure Portal** (portal.azure.com)
2. Click the **Cloud Shell** icon (>_) in the top navigation bar
3. Ensure you're using the **Bash** environment

**Verify Terraform installation:**

```bash
terraform version
```

You should see `Terraform v1.11.0` or similar.

### Step 2: Create Terraform Project Directory

**Create and navigate to project directory:**

```bash
mkdir azure-iot-terraform
cd azure-iot-terraform
```

---

## Part 2: Create Terraform Configuration Files

You'll create 4 Terraform files to define your IoT infrastructure:

1. **providers.tf** - Configure Terraform and Azure provider
2. **variables.tf** - Define input variables
3. **main.tf** - Define Azure resources (IoT Hub, Storage, Routing)
4. **outputs.tf** - Define values to display after deployment

### Step 3: Create providers.tf

**Create the file:**

```bash
nano providers.tf
```

**Copy and paste this content:**

```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Specifies azurerm provider version 3.x
- Simpler than Exercise 14 (no random or azapi providers needed)
- `features {}` is required but can be empty for basic deployments

### Step 4: Create variables.tf

**Create the file:**

```bash
nano variables.tf
```

**Copy and paste this content:**

```hcl
variable "resource_group_name" {
  description = "Name of the resource group"
  default     = "iot-terraform-rg"
}

variable "location" {
  description = "Azure region"
  default     = "uksouth"
}

variable "iot_hub_name" {
  description = "Name of the IoT Hub"
  default     = "terraform-iot-hub"
}

variable "storage_account_name" {
  description = "Name of the storage account"
  default     = "terraformiotstorage"
}

variable "container_name" {
  description = "Name of the blob container"
  default     = "telemetrydata"
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Defines 5 variables with default values
- Variables make configuration reusable and customizable
- Storage account name must be globally unique (add random suffix if needed)

**Important:** If you get a naming conflict later, change `storage_account_name` to include random numbers (e.g., `"terraformiotstorage12345"`).

### Step 5: Create main.tf

**Create the file:**

```bash
nano main.tf
```

**Copy and paste this content:**

```hcl
# Create a resource group
resource "azurerm_resource_group" "iot_rg" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_iothub" "iothub" {
  name                = var.iot_hub_name
  resource_group_name = azurerm_resource_group.iot_rg.name
  location            = azurerm_resource_group.iot_rg.location

  sku {
    name     = "F1" # Free tier, 8000 messages per day
    capacity = "1"
  }

  tags = {
    purpose = "telemetry"
  }
}

resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.iot_rg.name
  location                 = azurerm_resource_group.iot_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "container" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = "private"
}

resource "azurerm_iothub_endpoint_storage_container" "telemetry_endpoint" {
  resource_group_name = azurerm_resource_group.iot_rg.name
  iothub_id           = azurerm_iothub.iothub.id
  name                = "telemetryEndpoint"

  connection_string          = azurerm_storage_account.storage.primary_blob_connection_string
  batch_frequency_in_seconds = 60
  max_chunk_size_in_bytes    = 10485760
  container_name             = azurerm_storage_container.container.name
  encoding                   = "JSON"
  file_name_format           = "{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}"
}

resource "azurerm_iothub_route" "telemetry_route" {
  resource_group_name = azurerm_resource_group.iot_rg.name
  iothub_name         = azurerm_iothub.iothub.name
  name                = "telemetryRoute"
  source              = "DeviceMessages"
  condition           = "true"
  endpoint_names      = [azurerm_iothub_endpoint_storage_container.telemetry_endpoint.name]
  enabled             = true
}

# Create IoT Hub shared access policy
resource "azurerm_iothub_shared_access_policy" "policy" {
  name                = "terraform-policy"
  resource_group_name = azurerm_resource_group.iot_rg.name
  iothub_name         = azurerm_iothub.iothub.name

  registry_read   = true
  registry_write  = true
  service_connect = true
  device_connect  = true
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this creates:**

1. **Resource Group** - Container for all resources
2. **IoT Hub** - F1 (free tier) with 8,000 messages/day limit
3. **Storage Account** - Standard LRS for cost-effective storage
4. **Blob Container** - Named "telemetrydata" for storing messages
5. **Storage Endpoint** - Connects IoT Hub to Blob Storage
6. **Route** - Routes ALL device messages to storage (`condition = "true"`)
7. **Shared Access Policy** - For managing devices and getting connection strings

**Key Terraform IoT Resources:**

- `azurerm_iothub` - The IoT Hub itself
- `azurerm_iothub_endpoint_storage_container` - Defines where to route messages
- `azurerm_iothub_route` - Defines routing logic (condition and endpoint)
- `azurerm_iothub_shared_access_policy` - Access permissions

**Routing Difference from Exercise 13:**
- **Exercise 13 (Bicep)**: Routes only messages with `level="storage"` property
- **Exercise 15 (Terraform)**: Routes ALL messages (`condition = "true"`)

### Step 6: Create outputs.tf

**Create the file:**

```bash
nano outputs.tf
```

**Copy and paste this content:**

```hcl
output "iot_hub_name" {
  value = azurerm_iothub.iothub.name
}

output "iot_hub_connection_string" {
  value     = azurerm_iothub_shared_access_policy.policy.primary_connection_string
  sensitive = true
}

output "storage_account_name" {
  value = azurerm_storage_account.storage.name
}

output "blob_container_name" {
  value = azurerm_storage_container.container.name
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Outputs IoT Hub name for reference
- Outputs connection string (marked sensitive, won't display by default)
- Outputs storage account and container names
- Use `terraform output` command to view these later

---

## Part 3: Deploy Infrastructure with Terraform

### Step 7: Initialize Terraform

**Run terraform init:**

```bash
terraform init -upgrade
```

**What this does:**
- Downloads Azure provider plugin
- Initializes the working directory
- Creates `.terraform` directory and lock file

**Expected output:**
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/azurerm versions matching "~> 3.0"...
- Installing hashicorp/azurerm v3.x.x...

Terraform has been successfully initialized!
```

### Step 8: Review the Execution Plan

**Create an execution plan:**

```bash
terraform plan -out main.tfplan
```

**Expected output:**
```
Terraform will perform the following actions:

  # azurerm_iothub.iothub will be created
  + resource "azurerm_iothub" "iothub" {
      + name     = "terraform-iot-hub"
      + sku {
          + name     = "F1"
          + capacity = 1
        }
    }

  # ... (7 total resources)

Plan: 7 to add, 0 to change, 0 to destroy.
```

**Review the plan** to ensure correct region and resource names.

### Step 9: Apply the Configuration

**Deploy the infrastructure:**

```bash
terraform apply main.tfplan
```

**Wait 3-4 minutes**. You'll see progress as each resource is created.

**Expected output:**
```
azurerm_resource_group.iot_rg: Creating...
azurerm_resource_group.iot_rg: Creation complete after 2s
azurerm_iothub.iothub: Creating...
azurerm_storage_account.storage: Creating...
...
azurerm_iothub_route.telemetry_route: Creation complete after 3m15s

Apply complete! Resources: 7 added, 0 changed, 0 destroyed.

Outputs:

blob_container_name = "telemetrydata"
iot_hub_name = "terraform-iot-hub"
storage_account_name = "terraformiotstorage"
```

**Important:** Save the IoT Hub name for the next steps!

### Step 10: View Sensitive Outputs

The connection string is marked sensitive and won't display automatically.

**View the IoT Hub connection string:**

```bash
terraform output -raw iot_hub_connection_string
```

You'll see something like:
```
HostName=terraform-iot-hub.azure-devices.net;SharedAccessKeyName=terraform-policy;SharedAccessKey=...
```

**Note:** This is the **IoT Hub-level connection string**, not a device connection string. We'll create a device next.

---

## Part 4: Create Device and Configure Simulator

### Step 11: Create IoT Device

**Create a device identity:**

```bash
IOT_HUB_NAME=$(terraform output -raw iot_hub_name)
DEVICE_ID="terraform-device-01"
```

```bash
az iot hub device-identity create \
  --hub-name $IOT_HUB_NAME \
  --device-id $DEVICE_ID
```

**Get device connection string:**

```bash
az iot hub device-identity connection-string show \
  --hub-name $IOT_HUB_NAME \
  --device-id $DEVICE_ID \
  --output table
```

**Important:** Copy the **device connection string** - you'll need it for the simulator.

### Step 12: Configure Device Simulator

The simulator code is already provided in `simple_azure_device_simulator.py`.

**View the simulator code:**

```bash
cat simple_azure_device_simulator.py
```

**Key points in the code:**
- Uses Azure IoT SDK (same as Exercise 13)
- Sends temperature, humidity, pressure data
- Includes custom property `level="storage"` (not needed here since we route all messages)
- Sends messages every 10 seconds

**Update the connection string:**

```bash
nano simple_azure_device_simulator.py
```

**Change line 9** from:
```python
conn_str = "connection_string"
```

To your actual device connection string:
```python
conn_str = "HostName=terraform-iot-hub.azure-devices.net;DeviceId=terraform-device-01;SharedAccessKey=..."
```

**Save**: `Ctrl+X`, `Y`, `Enter`

### Step 13: Run Device Simulator

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

This installs `azure-iot-device` SDK.

**Run the simulator:**

```bash
python simple_azure_device_simulator.py
```

**Expected output:**
```
Connecting to Azure IoT
Connected to Azure IoT
Message sent: {"temperature": 24.5, "humidity": 52.3, "pressure": 1012.1}
Message sent: {"temperature": 25.1, "humidity": 53.8, "pressure": 1013.5}
```

**Keep the simulator running** for at least 2-3 minutes to ensure data is batched and written to storage.

---

## Part 5: Verify Data Flow to Blob Storage

### Step 14: Check Data in Azure Portal

**Wait 1-2 minutes** for IoT Hub to batch and write data (configured to batch every 60 seconds).

**Option 1: Via Azure Portal**

1. Navigate to your Storage Account in Azure Portal
2. Search for the storage account name (from `terraform output`)
3. Click **Storage Browser** → **Blob containers**
4. Click on **telemetrydata** container
5. Navigate through folders: `{iot-hub-name}/{partition}/YYYY/MM/DD/HH/mm/`
6. Download and open a JSON file

**Option 2: Via Azure CLI**

**List blobs:**

```bash
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
CONTAINER=$(terraform output -raw blob_container_name)

az storage blob list \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER \
  --output table \
  --auth-mode login
```

**Download a blob:**

```bash
# Get the first blob name
BLOB_NAME=$(az storage blob list \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER \
  --auth-mode login \
  --query "[0].name" -o tsv)

# Download it
az storage blob download \
  --account-name $STORAGE_ACCOUNT \
  --container-name $CONTAINER \
  --name "$BLOB_NAME" \
  --file telemetry-data.json \
  --auth-mode login

# View content
cat telemetry-data.json
```

**Expected content:**

```json
{
  "temperature": 24.5,
  "humidity": 52.3,
  "pressure": 1012.1
}
{
  "temperature": 25.1,
  "humidity": 53.8,
  "pressure": 1013.5
}
```

Each file contains multiple JSON objects (one per line).

---

## Part 6: Compare Terraform vs Bicep

### Step 15: Side-by-Side Comparison

**Terraform (Exercise 15):**
- **Pros**: Multi-cloud, mature ecosystem, detailed state management
- **Cons**: More files, requires state management, learning curve
- **Files**: 4 separate .tf files
- **Routing**: All messages automatically routed

**Bicep (Exercise 13):**
- **Pros**: Azure-native, simpler syntax, no state file to manage
- **Cons**: Azure-only, newer (less mature)
- **Files**: 1 main.bicep file
- **Routing**: Conditional routing with custom properties

**Resource Declaration Comparison:**

**Terraform:**
```hcl
resource "azurerm_iothub" "iothub" {
  name                = var.iot_hub_name
  resource_group_name = azurerm_resource_group.iot_rg.name
  location            = azurerm_resource_group.iot_rg.location

  sku {
    name     = "F1"
    capacity = "1"
  }
}
```

**Bicep (Exercise 13):**
```bicep
resource IoTHub 'Microsoft.Devices/IotHubs@2023-06-30' = {
  name: iotHubName
  location: location
  sku: {
    name: skuName
    capacity: skuUnits
  }
}
```

**Key Differences:**
1. **Syntax**: Bicep uses `:` and `=`, Terraform uses `=` and `{}`
2. **Resource Type**: Bicep specifies API version, Terraform abstracts it
3. **References**: Terraform uses `.` notation, Bicep direct references
4. **State**: Terraform needs `terraform.tfstate`, Bicep tracks via Azure

---

## Troubleshooting

### No data in Blob Storage

- **Wait longer**: Batching frequency is 60 seconds, plus processing time
- **Check simulator**: Ensure it's connected and sending messages
- **Check routing**: Verify route is enabled in Azure Portal → IoT Hub → Message routing
- **Check container**: Ensure container exists and route points to correct name

### Terraform init fails

- **Check internet**: Cloud Shell needs connectivity
- **Clear cache**: Delete `.terraform` directory and retry
- **Check provider version**: Ensure `~> 3.0` is correct

### Apply fails with "name already in use"

- **Storage account name conflict**: Change `storage_account_name` variable to include random suffix
- **IoT Hub name conflict**: Change `iot_hub_name` variable to be globally unique
- **Resource group exists**: Delete existing group or use different name

### Device connection fails

- **Wrong connection string**: Ensure you copied the **device** connection string, not IoT Hub connection string
- **Device doesn't exist**: Create device with `az iot hub device-identity create`
- **Check IoT Hub name**: Verify simulator uses correct hostname

### "InvalidParameter" for storage endpoint

- **Container doesn't exist**: Ensure storage container is created before endpoint
- **Check dependencies**: Terraform should handle this automatically
- **Retry deployment**: Sometimes Azure needs a moment; run `terraform apply` again

---

## Cleanup

**Important:** Delete all resources to avoid charges!

### Step 16: Destroy Infrastructure

**Create destroy plan:**

```bash
terraform plan -destroy -out main.destroy.tfplan
```

**Review the plan** - ensure it's destroying the correct resources.

**Apply the destroy plan:**

```bash
terraform apply main.destroy.tfplan
```

Wait 2-3 minutes. All 7 resources will be deleted.

**Verify cleanup:**

```bash
az group list --output table | grep iot-terraform
```

The resource group should be gone.

---

## Summary and Learning Outcomes

Congratulations! You've deployed IoT infrastructure using Terraform. You learned:

✅ **Terraform for IoT**: Deploying IoT Hub and storage with message routing
✅ **Terraform IoT Resources**: `azurerm_iothub`, routing endpoints, and routes
✅ **Message Routing**: Automatic routing of all device messages to storage
✅ **State Management**: Working with terraform.tfstate
✅ **Terraform Outputs**: Retrieving connection strings and resource names
✅ **Device Integration**: Connecting Python simulator to Terraform-deployed infrastructure
✅ **Terraform vs Bicep**: Hands-on comparison of two IaC approaches

### Architecture Pattern Reinforced

This exercise reinforces the **Cold Path** storage pattern:
- Devices send telemetry to IoT Hub
- IoT Hub automatically routes to Blob Storage
- Data stored for long-term analytics, compliance, ML training

### Terraform vs Bicep - When to Use Each

**Use Terraform when:**
- Working with multiple cloud providers (AWS, GCP, Azure)
- Need mature tooling and large community
- Want explicit state management control
- Team already uses Terraform

**Use Bicep when:**
- Azure-only workloads
- Want simpler syntax and fewer files
- Prefer Azure-native tools
- Don't want to manage state files

**Both are excellent choices** - the "best" tool depends on your specific needs!

## Next Steps

- Modify the route condition to filter messages (like Exercise 13's `level="storage"`)
- Add a second route to send data to Event Grid or Service Bus
- Deploy this same architecture to AWS using Terraform (use AWS IoT Core)
- Compare deployment times: Bicep vs Terraform
- Add Terraform modules to reuse this IoT configuration
- Implement remote state storage in Azure Storage Account
- Add more complex routing with multiple endpoints
- Create Terraform workspaces for dev/staging/prod environments

## Additional Resources

- [Terraform Azure IoT Hub Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/iothub)
- [Terraform vs Bicep Comparison](https://docs.microsoft.com/azure/developer/terraform/comparing-terraform-and-bicep)
- [Azure IoT Hub Routing](https://docs.microsoft.com/azure/iot-hub/iot-hub-devguide-messages-d2c)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)

---

## Reference: Key Terraform IoT Resources

**IoT Hub:**
```hcl
resource "azurerm_iothub" "example" {
  name                = "my-iothub"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location

  sku {
    name     = "F1"  # or "S1", "S2", "S3"
    capacity = "1"
  }
}
```

**Storage Endpoint:**
```hcl
resource "azurerm_iothub_endpoint_storage_container" "example" {
  resource_group_name = azurerm_resource_group.example.name
  iothub_id           = azurerm_iothub.example.id
  name                = "endpoint-name"

  connection_string          = azurerm_storage_account.example.primary_blob_connection_string
  batch_frequency_in_seconds = 60
  container_name             = "container-name"
  encoding                   = "JSON"
}
```

**Route:**
```hcl
resource "azurerm_iothub_route" "example" {
  resource_group_name = azurerm_resource_group.example.name
  iothub_name         = azurerm_iothub.example.name
  name                = "route-name"

  source         = "DeviceMessages"
  condition      = "true"  # or custom condition
  endpoint_names = [azurerm_iothub_endpoint_storage_container.example.name]
  enabled        = true
}
```
