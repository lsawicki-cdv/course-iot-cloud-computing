# Azure IoT Hub with Blob Storage - Bicep Deployment

> Using AWS instead? Follow the [AWS version of this exercise](aws/readme.md).

In this exercise, you'll deploy a complete IoT infrastructure using **Bicep** (Infrastructure as Code) and learn about **message routing** in Azure IoT Hub. You'll see how IoT Hub can automatically route messages to different destinations based on custom properties.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Architecture Overview

This exercise demonstrates a complete device-to-storage data pipeline:

```
IoT Device (Python Simulator)
    ↓ (MQTT with Azure IoT SDK)
Azure IoT Hub
    ↓ (Message Routing based on custom properties)
Azure Blob Storage (stores telemetry as JSON files)
```

### Key Concepts

**Message Routing**: IoT Hub can automatically route messages to different endpoints based on:
- Message properties
- Message body content
- Device twin tags
- Device ID

In this exercise, messages with the custom property `level="storage"` are routed to Blob Storage.

### What You'll Learn

- How to deploy IoT Hub infrastructure using Bicep
- Understanding IoT Hub message routing configuration
- Working with Azure IoT Device SDK (connection string authentication)
- How IoT Hub automatically stores messages in Blob Storage
- Bicep resource dependencies and outputs
- Custom message properties for routing decisions

## Tested Environments

- Ubuntu 24.04/26.04
- Python 3.10+ (tested with 3.12, `azure-iot-device` 2.13.0)
- Azure CLI 2.50+ (tested with 2.92)
- Bicep CLI (included with Azure CLI)

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- Python 3.10 or higher installed
- VS Code installed
- Azure CLI installed and logged in
- Basic understanding of IoT Hub (complete Exercise 6 first)
- Basic understanding of Bicep (complete Exercise 12 first)

---

## Part 1: Understand the Bicep Template

### Step 1: Examine the Bicep Configuration

Open `main.bicep` and review its structure. This template creates three main resources:

**Parameters** (lines 1-20):

```bicep
param projectName string = 'contoso'
param location string = resourceGroup().location
@allowed([
  'F1'
  'S1'
])
param skuName string = 'F1'
param skuUnits int = 1
param d2cPartitions int = 2
```

- `projectName`: Prefix for all resource names (1-11 characters)
- `location`: Inherits from resource group
- `skuName`: IoT Hub tier (F1 = Free tier, S1 = Standard tier)
- `skuUnits`: Number of IoT Hub units (determines message capacity)
- `d2cPartitions`: Partitions for device-to-cloud messages (affects throughput; the F1 tier allows only 2)

**Variables** (lines 22-26):

```bicep
var iotHubName = '${projectName}Hub${uniqueString(resourceGroup().id)}'
var storageAccountName = '${toLower(projectName)}${uniqueString(resourceGroup().id)}'
var storageEndpoint = '${projectName}StorageEndpoint'
var storageRoute = '${projectName}StorageRoute'
var storageContainerName = '${toLower(projectName)}results'
```

**Resources Deployed**:

1. **Storage Account** (lines 28-40): Blob storage for IoT telemetry
2. **Blob Container** (lines 42-50): Container within storage account
3. **IoT Hub** (lines 52-120): Main IoT Hub resource with message routing

**Key Bicep Features Demonstrated**:

**Message Routing Configuration** (lines 67-101):
- **Storage Endpoint**: Defines where to send messages (Blob Storage)
- **Route**: Condition-based routing (`level="storage"`)
- **Fallback Route**: Default route for messages not matching any condition

**File Naming Pattern** (line 73):
```bicep
fileNameFormat: '{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}'
```
This creates organized directory structure in Blob Storage by date/time.

**Outputs** (lines 122-127):
```bicep
output name string = IoTHub.name
output resourceId string = IoTHub.id
output resourceGroupName string = resourceGroup().name
output location string = location
output storageAccountName string = storageAccount.name
output storageContainerName string = storageContainerName
```
Outputs provide important information after deployment.

---

## Part 2: Deploy Infrastructure with Bicep

### Step 2: Deploy Using Azure Cloud Shell

Open **Azure Cloud Shell** from the Azure Portal.

**Option A: Using Bash (recommended)**

**Set the resource group name:**

```bash
RESOURCE_GROUP="cloud-computing-iot-hub"
```

Set the Azure region (change if needed):

```bash
LOCATION="uksouth"
```

Set the project name (1-11 characters, used as prefix):

```bash
PROJECT_NAME="contoso"
```

**Create the resource group:**

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 3: Deploy the Bicep Template

**Option A: Using Bash (recommended)**

**Deploy IoT Hub and Storage infrastructure:**

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters projectName=$PROJECT_NAME
```

**Wait 3-5 minutes for deployment to complete**. You'll see output showing the deployed resources.

**Note**: The template creates a **Free (F1)** IoT Hub. A subscription can have only **one** F1 hub: if you still have one from Exercise 6 or 11, delete it first, or deploy a Standard hub with `--parameters projectName=$PROJECT_NAME skuName=S1 d2cPartitions=4` (about $25 per month, billed per day - delete it right after the exercise).

**View deployment outputs:**

```bash
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.outputs
```

This shows the IoT Hub name, resource ID, location, storage account name and container name.

**Option B: Using PowerShell**

**Set the resource group name:**

```powershell
$RESOURCE_GROUP="cloud-computing-iot-hub"
```

Set the Azure region (change if needed):

```powershell
$LOCATION="uksouth"
```

Set the project name (1-11 characters, used as prefix):

```powershell
$PROJECT_NAME="contoso"
```

**Create the resource group:**

```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Deploy IoT Hub and Storage infrastructure:**

```powershell
az deployment group create `
  --resource-group $RESOURCE_GROUP `
  --template-file main.bicep `
  --parameters projectName=$PROJECT_NAME
```

**Wait 3-5 minutes for deployment to complete**. You'll see output showing the deployed resources.

**Note**: The template creates a **Free (F1)** IoT Hub. A subscription can have only **one** F1 hub: if you still have one from Exercise 6 or 11, delete it first, or deploy a Standard hub with `--parameters projectName=$PROJECT_NAME skuName=S1 d2cPartitions=4` (about $25 per month, billed per day - delete it right after the exercise).

**View deployment outputs:**

```powershell
az deployment group show `
  --resource-group $RESOURCE_GROUP `
  --name main `
  --query properties.outputs
```

This shows the IoT Hub name, resource ID, location, storage account name and container name.

### Step 4: Verify Deployed Resources

**Option A: Using Bash (recommended)**

**List all resources:**

```bash
az resource list --resource-group $RESOURCE_GROUP --output table
```

You should see:
- Storage account (e.g., `contoso<unique-string>`)
- IoT Hub (e.g., `contosoHub<unique-string>`)

**Get IoT Hub name:**

```bash
IOT_HUB_NAME=$(az iot hub list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "Your IoT Hub name: $IOT_HUB_NAME"
```

**Get Storage Account name:**

```bash
STORAGE_ACCOUNT_NAME=$(az storage account list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "Your Storage Account name: $STORAGE_ACCOUNT_NAME"
```

**Option B: Using PowerShell**

**List all resources:**

```powershell
az resource list --resource-group $RESOURCE_GROUP --output table
```

You should see:
- Storage account (e.g., `contoso<unique-string>`)
- IoT Hub (e.g., `contosoHub<unique-string>`)

**Get IoT Hub name:**

```powershell
$IOT_HUB_NAME=$(az iot hub list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "Your IoT Hub name: $IOT_HUB_NAME"
```

**Get Storage Account name:**

```powershell
$STORAGE_ACCOUNT_NAME=$(az storage account list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "Your Storage Account name: $STORAGE_ACCOUNT_NAME"
```

---

## Part 3: Create IoT Device and Configure Simulator

### Step 5: Register Device in IoT Hub

**Option A: Using Bash (recommended)**

**Create a device identity:**

```bash
DEVICE_ID="my-bicep-device-01"
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

**Important:** Copy the **connection string** - you'll need it for the device simulator.

The connection string looks like:
```
HostName=contosoHub....azure-devices.net;DeviceId=my-bicep-device-01;SharedAccessKey=...
```

**Option B: Using PowerShell**

**Create a device identity:**

```powershell
$DEVICE_ID="my-bicep-device-01"
```

```powershell
az iot hub device-identity create `
  --hub-name $IOT_HUB_NAME `
  --device-id $DEVICE_ID
```

**Get device connection string:**

```powershell
az iot hub device-identity connection-string show `
  --hub-name $IOT_HUB_NAME `
  --device-id $DEVICE_ID `
  --output table
```

**Important:** Copy the **connection string** - you'll need it for the device simulator.

The connection string looks like:
```
HostName=contosoHub....azure-devices.net;DeviceId=my-bicep-device-01;SharedAccessKey=...
```

### Step 6: Configure Device Simulator

**On your local machine**, navigate to the exercise directory:

```bash
cd 13-iac-iot-routing
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

This installs `azure-iot-device` SDK version 2.13.0.

**Update the connection string:**

Open `simple_azure_device_simulator.py` and update line 9 (replace `connection_string`):

```python
conn_str = "HostName=contosoHub....azure-devices.net;DeviceId=my-bicep-device-01;SharedAccessKey=..."
```

Paste your actual connection string from Step 5.

### Step 7: Understand the Device Simulator Code

The simulator has two key features:

**1. Uses Azure IoT SDK** (lines 10-13):
```python
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)
device_client.connect()
```
This is simpler than the raw MQTT client from Exercise 6 - the SDK still uses MQTT, but it creates the SAS token from the connection string and handles the topics and reconnecting for you.

**2. Adds Custom Message Property** (line 37):
```python
message.custom_properties["level"] = "storage"
```
This property triggers the routing rule defined in the Bicep template!

**Message Routing Logic:**
- Messages WITH `level="storage"` → Routed to Blob Storage
- Messages WITHOUT this property → Sent to default Event Hub endpoint

---

## Part 4: Run Simulator and Verify Data Flow

### Step 8: Run the Device Simulator

**Start the simulator:**

```bash
python simple_azure_device_simulator.py
```

You should see output like:

```
Connecting to Azure IoT
Connected to Azure IoT
Message sent: {"temperature": 24.5, "humidity": 52.3, "pressure": 1012.1}
Message sent: {"temperature": 25.1, "humidity": 53.8, "pressure": 1013.5}
```

The simulator sends telemetry every 10 seconds. **Keep it running** for at least 2-3 minutes to ensure data is written to storage.

### Step 9: Check Message Routing in Azure Portal

**View IoT Hub metrics:**

1. In Azure Portal, navigate to your IoT Hub
2. Click **Metrics** in the left menu
3. Add metric: **Routing: Data delivered to storage**
4. You should see messages being routed

**View message routing configuration:**

1. In IoT Hub, click **Message routing**
2. Review the **Routes** tab - you'll see `contosoStorageRoute`
3. Click on the route to see the condition: `level="storage"`
4. Review the **Endpoints** tab - you'll see the storage endpoint

### Step 10: Verify Data in Blob Storage

**Wait 2-3 minutes** for IoT Hub to batch and write data to storage. IoT Hub writes data in batches every 100 seconds (configured in Bicep: `batchFrequencyInSeconds: 100`).

**Option 1: Via Azure Portal**

1. Navigate to your Storage Account in Azure Portal
2. Click **Storage Browser** in the left menu
3. Expand **Blob containers**
4. Click on `contosoresults` container
5. Navigate through the folder hierarchy: `{iot-hub-name}/{partition}/YYYY/MM/DD/HH/mm/`
6. Download and open one of the JSON files

**Option 2: Via Azure CLI**

The commands use `--auth-mode key`: the CLI reads the storage account key with your Azure account. (`--auth-mode login` would need the **Storage Blob Data Reader** role on the storage account, which the subscription Owner doesn't get automatically.)

**Using Bash:**

**List blobs in container:**

```bash
az storage blob list \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name "${PROJECT_NAME}results" \
  --output table \
  --auth-mode key
```

**Download a blob to inspect:**

```bash
# Get the first blob name
BLOB_NAME=$(az storage blob list \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name "${PROJECT_NAME}results" \
  --auth-mode key \
  --query "[0].name" -o tsv)

# Download the blob
az storage blob download \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name "${PROJECT_NAME}results" \
  --name "$BLOB_NAME" \
  --file downloaded-telemetry.json \
  --auth-mode key

# View the content
cat downloaded-telemetry.json
```

**Using PowerShell:**

**List blobs in container:**

```powershell
az storage blob list `
  --account-name $STORAGE_ACCOUNT_NAME `
  --container-name "${PROJECT_NAME}results" `
  --output table `
  --auth-mode key
```

**Download a blob to inspect:**

```powershell
# Get the first blob name
$BLOB_NAME=$(az storage blob list `
  --account-name $STORAGE_ACCOUNT_NAME `
  --container-name "${PROJECT_NAME}results" `
  --auth-mode key `
  --query "[0].name" -o tsv)

# Download the blob
az storage blob download `
  --account-name $STORAGE_ACCOUNT_NAME `
  --container-name "${PROJECT_NAME}results" `
  --name "$BLOB_NAME" `
  --file downloaded-telemetry.json `
  --auth-mode key

# View the content
cat downloaded-telemetry.json
```

**Expected content** (shortened):

```json
{"EnqueuedTimeUtc":"2026-11-17T17:01:08.4390000Z","Properties":{"level":"storage"},"SystemProperties":{"connectionDeviceId":"my-bicep-device-01","contentType":"application/json","contentEncoding":"utf-8",...},"Body":{"temperature": 25.32, "humidity": 53.82, "pressure": 940.90}}
{"EnqueuedTimeUtc":"2026-11-17T17:01:18.7390000Z","Properties":{"level":"storage"},"SystemProperties":{...},"Body":{"temperature": 24.10, "humidity": 51.35, "pressure": 1012.12}}
```

Each file contains one JSON object per line, one per message. IoT Hub wraps each message: `Body` is the telemetry sent by the device, `Properties` holds the custom properties (`level`), and `SystemProperties` holds what IoT Hub knows about the message (device ID, time, content type). The body is readable JSON because the simulator sets `content_type` to `application/json` and `content_encoding` to `utf-8`; without them it would be base64-encoded.

---

## Part 5: Explore Message Routing

### Step 11: Experiment with Message Routing

**Modify the device simulator to send different message types:**

Open `simple_azure_device_simulator.py` and modify the custom property:

**Option 1: Remove the routing property**

Comment out line 37:
```python
# message.custom_properties["level"] = "storage"
```

Restart the simulator. Messages will now go to the default Event Hub endpoint instead of Blob Storage.

**Option 2: Add multiple properties**

Add different properties for more complex routing:
```python
message.custom_properties["level"] = "storage"
message.custom_properties["sensor_type"] = "temperature"
message.custom_properties["location"] = "warehouse-1"
```

**Option 3: Conditional routing based on values**

```python
if temperature > 25:
    message.custom_properties["level"] = "storage"
    message.custom_properties["alert"] = "high-temp"
```

### Step 12: Compare the Routes in the Metrics (Default Route)

Messages that don't match the storage route go to the **fallback route**, which delivers them to the built-in endpoint `messages/events` (the endpoint that Stream Analytics read in Exercise 11). Run the simulator without the property for a minute (Option 1 in Step 11), then compare where the messages went:

1. In Azure Portal, navigate to your IoT Hub → **Metrics**
2. Add the metric **Routing: messages delivered to storage** (aggregation **Sum**)
3. Click **Add metric** and add **Routing: messages delivered to fallback** (aggregation **Sum**)
4. Messages with `level="storage"` count in the first metric, messages without it in the second (metrics appear with a delay of 1-3 minutes)

**Or with Azure CLI:**

**Using Bash:**

```bash
IOT_HUB_ID=$(az iot hub show --name $IOT_HUB_NAME --query id -o tsv)
az monitor metrics list \
  --resource $IOT_HUB_ID \
  --metrics d2c.endpoints.egress.storage d2c.telemetry.egress.fallback \
  --interval PT1H \
  --aggregation Total \
  --output table
```

**Using PowerShell:**

```powershell
$IOT_HUB_ID=$(az iot hub show --name $IOT_HUB_NAME --query id -o tsv)
az monitor metrics list `
  --resource $IOT_HUB_ID `
  --metrics d2c.endpoints.egress.storage d2c.telemetry.egress.fallback `
  --interval PT1H `
  --aggregation Total `
  --output table
```

To see the content of the messages on the built-in endpoint, use [Azure IoT Explorer](https://github.com/Azure/azure-iot-explorer/releases) (**Telemetry** tab of the device). `az iot hub monitor-events` can also show them, but it needs the `uamqp` package, which fails to install with recent Azure CLI versions.

---

## Understanding the Deployment

### Bicep Resource Dependencies

The template automatically handles dependencies:

```
Storage Account (created first)
    ↓
Blob Container (depends on Storage Account)
    ↓
IoT Hub (references Storage Account connection)
```

Bicep uses implicit dependencies through resource references (`storageAccount.listKeys()`).

### IoT Hub SKU Comparison

| SKU | Tier | Cost | Daily Messages | Use Case |
|-----|------|------|----------------|----------|
| F1 | Free | Free | 8,000 | Development/Testing |
| S1 | Standard | $25/month | 400,000 | Production (small) |
| S2 | Standard | $250/month | 6,000,000 | Production (medium) |
| S3 | Standard | $2,500/month | 300,000,000 | Production (large) |

The template defaults to F1 (free, one per subscription, 2 partitions). To use the Standard tier, change the Bicep parameters:

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters projectName=$PROJECT_NAME skuName=S1 d2cPartitions=4
```

### Message Routing Best Practices

1. **Use specific conditions**: Avoid routing all messages to storage (expensive)
2. **Batch settings**: Balance between latency and cost
3. **Partitions**: More partitions = higher throughput but more files
4. **File format**: JSON is readable, Avro is more efficient
5. **Monitoring**: Set up alerts for routing failures

---

## Troubleshooting

### No data appearing in Blob Storage

- **Wait longer**: IoT Hub batches messages every 100 seconds
- **Check custom property**: Ensure `message.custom_properties["level"] = "storage"` is set
- **Verify routing**: In Portal, check Message Routing → Metrics
- **Check simulator**: Ensure device is connected and sending messages
- **Storage account access**: Verify IoT Hub has permission to write to storage
- **Check the metrics**: Step 12 shows if the messages go to storage or to the fallback route

### Device connection fails

- **Check connection string**: Ensure it's complete and correctly copied
- **Verify device exists**: Run `az iot hub device-identity list --hub-name $IOT_HUB_NAME`
- **Check device status**: Device might be disabled in IoT Hub
- **Network issues**: Ensure firewall allows HTTPS outbound to *.azure-devices.net

### Deployment fails with "SkuNotAvailable" or a free hub limit error

- **One free hub per subscription**: If you already have an F1 IoT Hub (`az iot hub list -o table`), delete it, or deploy with `skuName=S1 d2cPartitions=4` (paid)
- **Region limitation**: Not all SKUs available in all regions
- **Check quota**: You may have reached your subscription limit for IoT Hubs

### Deployment fails with an error about partitions

- **The F1 tier allows only 2 partitions**: Keep the default `d2cPartitions=2`; use 4 only with `skuName=S1`

### Cannot find blob container

- **Check container name**: Should be `{projectName}results` (lowercase)
- **Wait for messages**: Container won't have folders until messages are routed
- **Verify storage endpoint**: In IoT Hub, check Message Routing → Endpoints

### "InvalidAuthorizationAudience" error in simulator

- **Wrong connection string**: Ensure you copied the device connection string, not the IoT Hub connection string
- **Device doesn't exist**: Create the device identity first
- **Expired credentials**: For SAS token, regenerate a new one

---

## Cleanup

**Important:** Delete all resources to avoid ongoing charges!

### Option 1: Delete Resource Group (Recommended)

This deletes IoT Hub and Storage Account:

```bash
az group delete --name cloud-computing-iot-hub --yes --no-wait
```

### Option 2: Delete Individual Resources

**Delete IoT Hub:**

```bash
az iot hub delete --name $IOT_HUB_NAME --resource-group $RESOURCE_GROUP
```

**Delete Storage Account:**

```bash
az storage account delete \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --yes
```

---

## Summary and Learning Outcomes

Congratulations! You've deployed a complete IoT infrastructure using Bicep. You learned:

✅ **Bicep for IoT**: Deploying IoT Hub and storage using Infrastructure as Code
✅ **Message Routing**: Conditionally routing messages based on properties
✅ **Azure IoT SDK**: Using connection strings for device authentication
✅ **Blob Storage Integration**: Automatic storage of IoT telemetry
✅ **Custom Properties**: Adding metadata to messages for routing decisions
✅ **Resource Dependencies**: How Bicep manages deployment order
✅ **Bicep Outputs**: Retrieving resource information after deployment

### Architecture Pattern: Cold Path Storage

This exercise demonstrates the **Cold Path** pattern in IoT:
- **Hot Path**: Real-time processing (Stream Analytics, Functions)
- **Cold Path**: Historical storage for analytics (Blob Storage, Data Lake)

Messages are automatically archived to Blob Storage for:
- Long-term storage
- Batch analytics
- Machine learning training data
- Compliance and auditing
- Cost-effective historical queries

### Comparison: Exercise 6 vs Exercise 13

| Feature | Exercise 6 (Manual) | Exercise 13 (Bicep) |
|---------|---------------------|---------------------|
| Deployment | Azure Portal clicks | Code (repeatable) |
| Protocol | MQTT (manual auth) | MQTT (SDK, connection string) |
| Message Routing | Not configured | Automated to Blob |
| Infrastructure | Manual setup | Version controlled |
| Time to Deploy | 15-20 minutes | 3-5 minutes |

## Optional Next Steps

- Modify the Bicep template to add multiple routing rules (e.g., alerts to Event Grid)
- Change the file format from JSON to Avro for more efficient storage
- Add Azure Stream Analytics to process messages in real-time
- Implement device twins to manage device configuration from the cloud
- Compare this exercise with Exercise 15 (Terraform) - same architecture, different IaC tool
- Add Azure Functions triggered by new blobs for automatic processing
- Implement retention policies to automatically delete old telemetry data
- Set up monitoring alerts for routing failures

## Additional Resources

- [Azure IoT Hub Message Routing](https://docs.microsoft.com/azure/iot-hub/iot-hub-devguide-messages-d2c)
- [Bicep IoT Hub Reference](https://docs.microsoft.com/azure/templates/microsoft.devices/iothubs)
- [Azure IoT Device SDK](https://github.com/Azure/azure-iot-sdk-python)
- [IoT Hub Pricing](https://azure.microsoft.com/pricing/details/iot-hub/)

---

## Reference: Bicep Template Structure

**Key sections in main.bicep:**

```bicep
// 1. Parameters - User inputs
param projectName string = 'contoso'
param skuName string = 'F1'

// 2. Variables - Computed values
var iotHubName = '${projectName}Hub${uniqueString(resourceGroup().id)}'

// 3. Resources - What to deploy
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = { ... }
resource IoTHub 'Microsoft.Devices/IotHubs@2023-06-30' = { ... }

// 4. Outputs - Return values
output name string = IoTHub.name
```

**Common Bicep Functions Used:**

- `uniqueString()` - Generate unique suffixes
- `toLower()` - Convert to lowercase
- `listKeys()` - Retrieve storage account keys
- `environment()` - Get Azure environment info
- `resourceGroup()` - Access resource group properties

