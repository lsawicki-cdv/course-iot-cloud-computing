# Azure IoT Hub with Blob Storage - Bicep Deployment

In this exercise, you'll deploy a complete IoT infrastructure using **Bicep** (Infrastructure as Code) and learn about **message routing** in Azure IoT Hub. You'll see how IoT Hub can automatically route messages to different destinations based on custom properties.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Architecture Overview

This exercise demonstrates a complete device-to-storage data pipeline:

```
IoT Device (Python Simulator)
    ↓ (HTTPS with Azure IoT SDK)
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

- Ubuntu 22.04
- Python 3.10.12+
- Azure CLI 2.50+
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

**Parameters** (lines 1-16):

```bicep
param projectName string = 'contoso'
param location string = resourceGroup().location
param skuName string = 'S1'
param skuUnits int = 1
param d2cPartitions int = 4
```

- `projectName`: Prefix for all resource names (1-11 characters)
- `location`: Inherits from resource group
- `skuName`: IoT Hub tier (S1 = Standard tier, F1 = Free tier)
- `skuUnits`: Number of IoT Hub units (determines message capacity)
- `d2cPartitions`: Partitions for device-to-cloud messages (affects throughput)

**Variables** (lines 18-21):

```bicep
var iotHubName = '${projectName}Hub${uniqueString(resourceGroup().id)}'
var storageAccountName = '${toLower(projectName)}${uniqueString(resourceGroup().id)}'
var storageEndpoint = '${projectName}StorageEndpont'
var storageContainerName = '${toLower(projectName)}results'
```

**Resources Deployed**:

1. **Storage Account** (lines 23-35): Blob storage for IoT telemetry
2. **Blob Container** (lines 37-45): Container within storage account
3. **IoT Hub** (lines 47-114): Main IoT Hub resource with message routing

**Key Bicep Features Demonstrated**:

**Message Routing Configuration** (lines 61-95):
- **Storage Endpoint**: Defines where to send messages (Blob Storage)
- **Route**: Condition-based routing (`level="storage"`)
- **Fallback Route**: Default route for messages not matching any condition

**File Naming Pattern** (line 67):
```bicep
fileNameFormat: '{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}'
```
This creates organized directory structure in Blob Storage by date/time.

**Outputs** (lines 116-119):
```bicep
output name string = IoTHub.name
output resourceId string = IoTHub.id
output resourceGroupName string = resourceGroup().name
output location string = location
```
Outputs provide important information after deployment.

---

## Part 2: Deploy Infrastructure with Bicep

### Step 2: Deploy Using Azure Cloud Shell

Open **Azure Cloud Shell (Bash)** from the Azure Portal.

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

**Deploy IoT Hub and Storage infrastructure:**

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters projectName=$PROJECT_NAME
```

**Wait 2-3 minutes for deployment to complete**. You'll see output showing the deployed resources.

**View deployment outputs:**

```bash
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.outputs
```

This shows the IoT Hub name, resource ID, and location.

### Step 4: Verify Deployed Resources

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

---

## Part 3: Create IoT Device and Configure Simulator

### Step 5: Register Device in IoT Hub

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

### Step 6: Configure Device Simulator

**On your local machine**, navigate to the exercise directory:

```bash
cd 13-iot-hub-bicep
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

Open `simple_azure_device_simulator.py` and update line 9:

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
This is simpler than MQTT - the SDK handles authentication and protocol details.

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
2. Review the **Routes** tab - you'll see `ContosoStorageRoute`
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

**List blobs in container:**

```bash
az storage blob list \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name "${PROJECT_NAME}results" \
  --output table \
  --auth-mode login
```

**Download a blob to inspect:**

```bash
# Get the first blob name
BLOB_NAME=$(az storage blob list \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name "${PROJECT_NAME}results" \
  --auth-mode login \
  --query "[0].name" -o tsv)

# Download the blob
az storage blob download \
  --account-name $STORAGE_ACCOUNT_NAME \
  --container-name "${PROJECT_NAME}results" \
  --name "$BLOB_NAME" \
  --file downloaded-telemetry.json \
  --auth-mode login

# View the content
cat downloaded-telemetry.json
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

Each file contains multiple JSON objects (one per line) representing telemetry messages.

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

### Step 12: View Built-in Event Endpoint (Default Route)

If you want to see messages that don't match the storage route:

**In VS Code with Azure IoT Hub Extension:**

1. Install the Azure IoT Hub extension
2. Sign in to your Azure account
3. Find your IoT Hub in the Azure IoT Hub panel
4. Right-click and select **Start Monitoring Built-in Event Endpoint**
5. Remove the custom property from simulator and restart
6. You'll see messages appearing in VS Code output panel

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

The template defaults to S1. To use the free tier, change the Bicep parameter:

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters projectName=$PROJECT_NAME skuName=F1
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

### Device connection fails

- **Check connection string**: Ensure it's complete and correctly copied
- **Verify device exists**: Run `az iot hub device-identity list --hub-name $IOT_HUB_NAME`
- **Check device status**: Device might be disabled in IoT Hub
- **Network issues**: Ensure firewall allows HTTPS outbound to *.azure-devices.net

### Deployment fails with "SkuNotAvailable"

- **Region limitation**: Not all SKUs available in all regions
- **Use free tier**: Try `skuName=F1` instead of `S1`
- **Check quota**: You may have reached your subscription limit for IoT Hubs

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
| Protocol | MQTT (manual auth) | HTTPS (SDK) |
| Message Routing | Not configured | Automated to Blob |
| Infrastructure | Manual setup | Version controlled |
| Time to Deploy | 15-20 minutes | 3-5 minutes |

## Next Steps

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
param skuName string = 'S1'

// 2. Variables - Computed values
var iotHubName = '${projectName}Hub${uniqueString(resourceGroup().id)}'

// 3. Resources - What to deploy
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = { ... }
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

