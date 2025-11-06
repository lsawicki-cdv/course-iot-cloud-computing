# Serverless IoT Platform

In this exercise, you'll build a complete serverless IoT platform combining four Azure services. You'll create an end-to-end system where IoT devices send telemetry data that flows through Azure services and can be queried via a REST API.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Architecture Overview

```
IoT Device (Simulator)
    ↓ (MQTT/MQTTS)
Azure IoT Hub (receives telemetry)
    ↓ (message routing)
Azure Stream Analytics (processes & transforms)
    ↓ (writes data)
Azure Cosmos DB (NoSQL storage)
    ↑ (queries data)
Azure Functions (REST API)
    ↑ (HTTP requests)
Client (Postman / Frontend)
```

### What You'll Learn
- How to create and configure Azure IoT Hub for device connectivity
- How to use Azure Stream Analytics for real-time data processing
- How to store IoT data in Azure Cosmos DB (NoSQL database)
- How to build a REST API using Azure Functions (serverless compute)
- How to deploy Python-based Azure Functions
- How to test REST APIs using Postman

## Tested Environments
- Ubuntu 22.04/24.04
- Python 3.10.12+
- Azure Functions Core Tools v4

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- [VS Code](https://code.visualstudio.com/) installed
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local) installed
- [Postman](https://www.postman.com/) for API testing
- Completed Exercise 6 (IoT Hub) - we'll reuse the device simulator

---

## Part 1: Create Azure IoT Hub and Send Test Data

### Step 1: Create IoT Hub and Device

Open **Azure Cloud Shell (Bash)** from the Azure Portal.

**Set the environment variables one by one:**

Set the resource group name:
```bash
RESOURCE_GROUP="resourceGroupIotPlatform"
```

Set the Azure region (change if needed):
```bash
LOCATION="uksouth"
```

Set the IoT Hub name (**must be globally unique** - change this!):
```bash
IOT_HUB_NAME="cdv-iot-platform-hub-12345"
```

Set your device name:
```bash
IOT_DEVICE_NAME="my-iot-device-01"
```

**Create the resource group:**
```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Create the IoT Hub (this will take 2-3 minutes):**
```bash
az iot hub create \
  --resource-group $RESOURCE_GROUP \
  --name $IOT_HUB_NAME \
  --location $LOCATION \
  --sku F1 \
  --partition-count 2
```

**Important:** Save your IoT Hub name - you'll need it throughout this exercise!

**Create device identity:**
```bash
az iot hub device-identity create \
  --hub-name $IOT_HUB_NAME \
  --device-id $IOT_DEVICE_NAME
```

**Generate SAS token for device authentication:**
```bash
az iot hub generate-sas-token \
  --hub-name $IOT_HUB_NAME \
  --device-id $IOT_DEVICE_NAME \
  --output table
```

**Important:** Copy the **SAS token** - you'll need it for the device simulator.

### Step 2: Configure and Run Device Simulator

We'll reuse the MQTT device simulator from Exercise 6.

**On your local machine**, navigate to Exercise 6:
```bash
cd 6-paas-iot-hub
```

If you haven't already, create a virtual environment and install dependencies:

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**On Windows:**
```powershell
py -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt
```

**Configure the simulator:**

Open `simple_mqtt_device_simulator.py` and update these values:

Set your device ID:
```python
device_id = "my-iot-device-01"  # Must match the device ID you created
```

Set your SAS token (paste the full token):
```python
sas_token = "SharedAccessSignature sr=cdv-iot-platform-hub-..."  # Paste your SAS token here
```

Set your IoT Hub name:
```python
iot_hub_name = "cdv-iot-platform-hub-12345"  # Use your IoT Hub name
```

**Uncomment the authentication and security lines** (remove the `#` at the start):

```python
print(iot_hub_name+".azure-devices.net/" +
      device_id + "/?api-version=2021-04-12")
client.username_pw_set(username=iot_hub_name+".azure-devices.net/" +
                       device_id + "/?api-version=2021-04-12", password=sas_token)

client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None,
               cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
client.tls_insecure_set(False)
```

Update the connection settings to use Azure IoT Hub hostname and secure port:

```python
mqtt_hub_hostname = "cdv-iot-platform-hub-12345.azure-devices.net"  # Your IoT Hub hostname
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

**Keep the simulator running** - we need continuous data for testing later.

---

## Part 2: Create Azure Cosmos DB

Cosmos DB is a globally distributed NoSQL database that will store our IoT data and entities.

### Step 3: Create Cosmos DB Account, Database, and Containers

Go back to **Azure Cloud Shell**.

**Set the Cosmos DB account name (must be globally unique):**
```bash
COSMOS_DB_ACCOUNT_NAME="cosmos-iot-platform-12345"
```

Set the database name:
```bash
COSMOS_DB_DATABASE_NAME="iot-platform-database"
```

**Create Cosmos DB account (this takes 3-5 minutes):**
```bash
az cosmosdb create \
  --name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --locations regionName=$LOCATION \
  --enable-free-tier true \
  --default-consistency-level "Session"
```

**Create database:**
```bash
az cosmosdb sql database create \
  --account-name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --name $COSMOS_DB_DATABASE_NAME \
  --throughput 400
```

**Create container for IoT telemetry data:**
```bash
az cosmosdb sql container create \
  --account-name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --database-name $COSMOS_DB_DATABASE_NAME \
  --name "iot-data" \
  --partition-key-path "/deviceid"
```

**Create container for house data:**
```bash
az cosmosdb sql container create \
  --account-name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --database-name $COSMOS_DB_DATABASE_NAME \
  --name "house-data" \
  --partition-key-path "/id"
```

**Create container for room data:**
```bash
az cosmosdb sql container create \
  --account-name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --database-name $COSMOS_DB_DATABASE_NAME \
  --name "room-data" \
  --partition-key-path "/id"
```

**Get Cosmos DB endpoint:**
```bash
az cosmosdb show \
  --name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "documentEndpoint" \
  --output tsv
```

**Get Cosmos DB primary key:**
```bash
az cosmosdb keys list \
  --name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --type keys \
  --query "primaryMasterKey" \
  --output tsv
```

**Important:** Save both the **endpoint** and **primary key** - you'll need them for Azure Functions and Stream Analytics.

---

## Part 3: Create Azure Stream Analytics Job

Stream Analytics will read data from IoT Hub, transform it, and write it to Cosmos DB in real-time.

### Step 4: Create Stream Analytics Job

**Set the Stream Analytics job name:**
```bash
STREAM_ANALYTICS_JOB_NAME="stream-iot-data"
```

**Create Stream Analytics job:**
```bash
az stream-analytics job create \
  --resource-group $RESOURCE_GROUP \
  --name $STREAM_ANALYTICS_JOB_NAME \
  --location $LOCATION \
  --output-error-policy Stop
```

### Step 5: Configure Input and Output via Azure Portal

**The Azure CLI has limitations for configuring Stream Analytics inputs/outputs. We'll use the Azure Portal for this section.**

**Configure Input (IoT Hub):**

1. In Azure Portal, navigate to your Stream Analytics job: `stream-iot-data`
2. Click **Inputs** in the left menu
3. Click **+ Add input** → **IoT Hub**
4. Configure the input:
   - **Input alias**: `iothubinput`
   - **Select IoT Hub from your subscriptions**: Yes
   - **Subscription**: Your subscription
   - **IoT Hub**: Select your IoT Hub (`cdv-iot-platform-hub-...`)
   - **Consumer group**: `$Default`
   - **Shared access policy name**: `iothubowner`
   - **Endpoint**: `Messaging`
   - **Event serialization format**: `JSON`
   - **Encoding**: `UTF-8`
5. Click **Save**

**Configure Output (Cosmos DB):**

1. Click **Outputs** in the left menu
2. Click **+ Add output** → **Azure Cosmos DB**
3. Configure the output:
   - **Output alias**: `cosmosdboutput`
   - **Select Azure Cosmos DB from your subscriptions**: Yes
   - **Subscription**: Your subscription
   - **Account id**: Select your Cosmos DB account (`cosmos-iot-platform-...`)
   - **Database**: `iot-platform-database`
   - **Container name**: `iot-data`
   - **Document id**: Leave empty (auto-generated)
4. Click **Save**

### Step 6: Configure Stream Analytics Query

The query transforms the incoming IoT data and adds the required `deviceid` field for Cosmos DB partitioning.

1. Click **Query** in the left menu
2. Replace the existing query with:

```sql
SELECT
    temperature,
    humidity,
    pressure,
    timestamp,
    device_id as deviceid
INTO cosmosdboutput
FROM iothubinput
```

3. Click **Save query**
4. Click **Overview** in the left menu
5. Click **Start** to start the job
6. Select **Now** as the start time
7. Click **Start**

**Wait 1-2 minutes for the job to start**. The status will change from "Starting" to "Running".

### Step 7: Verify Data Flow

**Check if data is flowing into Cosmos DB:**

1. In Azure Portal, navigate to your Cosmos DB account
2. Go to **Data Explorer**
3. Expand `iot-platform-database` → `iot-data` → **Items**
4. You should see documents appearing with temperature, humidity, pressure, device_id, and timestamp fields

If you see data, congratulations! Your data pipeline is working:
**Device → IoT Hub → Stream Analytics → Cosmos DB**

---

## Part 4: Create Azure Functions REST API

Now we'll create a serverless REST API using Azure Functions to query and manage the IoT data.

### Step 8: Create Azure Function App

**Set the Function App name (must be globally unique):**
```bash
FUNCTION_APP_NAME="cdv-iot-platform-func-12345"
```

Set the storage account name (must be globally unique, lowercase, no hyphens):
```bash
STORAGE_ACCOUNT_NAME="iotfuncstorage12345"
```

**Create Storage Account (required for Functions):**
```bash
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS
```

**Create Function App:**
```bash
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --name $FUNCTION_APP_NAME \
  --storage-account $STORAGE_ACCOUNT_NAME \
  --runtime python \
  --functions-version 4 \
  --runtime-version 3.11 \
  --os-type Linux
```

**Important:** Save your Function App name and URL:
```bash
echo "Your Function App name: $FUNCTION_APP_NAME"
echo "Your Function App URL: https://$FUNCTION_APP_NAME.azurewebsites.net"
```

### Step 9: Update Function Code with Cosmos DB Credentials

**On your local machine**, navigate to the function app directory:
```bash
cd 11-serverless-iot-platform/iot-function-app
```

**Update each function with your Cosmos DB credentials:**

Open `device/__init__.py` and update lines 8-10:
```python
endpoint = "https://cosmos-iot-platform-12345.documents.azure.com:443/"  # Your Cosmos DB endpoint
key = "your-cosmos-db-primary-key-here"  # Your Cosmos DB primary key
```

Open `house/__init__.py` and update lines 8-10:
```python
endpoint = "https://cosmos-iot-platform-12345.documents.azure.com:443/"  # Your Cosmos DB endpoint
key = "your-cosmos-db-primary-key-here"  # Your Cosmos DB primary key
```

Open `rooms/__init__.py` and update lines 8-10:
```python
endpoint = "https://cosmos-iot-platform-12345.documents.azure.com:443/"  # Your Cosmos DB endpoint
key = "your-cosmos-db-primary-key-here"  # Your Cosmos DB primary key
```

### Step 10: Deploy Functions to Azure

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

**Deploy to Azure:**
```bash
func azure functionapp publish $FUNCTION_APP_NAME
```

Wait for deployment to complete (this takes 2-3 minutes). You should see output like:
```
Functions in cdv-iot-platform-func-12345:
    device - [httpTrigger]
        Invoke url: https://cdv-iot-platform-func-12345.azurewebsites.net/api/device

    house - [httpTrigger]
        Invoke url: https://cdv-iot-platform-func-12345.azurewebsites.net/api/house

    rooms - [httpTrigger]
        Invoke url: https://cdv-iot-platform-func-12345.azurewebsites.net/api/rooms
```

---

## Part 5: Test REST API with Postman

### Step 11: Get Function Access Key

Azure Functions are protected by access keys by default. Get your function key:

**Option 1: Via Azure Portal**
1. Navigate to your Function App in Azure Portal
2. Click **App keys** under **Functions** in left menu
3. Copy the **default** key under **Host keys**

**Option 2: Via Azure CLI**
```bash
az functionapp keys list \
  --name $FUNCTION_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "functionKeys.default" \
  --output tsv
```

**Important:** You'll add this key as `?code=<your-key>` to each API request URL.

### Step 12: Test API Endpoints

Open **Postman** and create the following requests:

#### 1. GET Device Data (Query IoT Telemetry)

**Request:**
- Method: `GET`
- URL: `https://<your-function-app-name>.azurewebsites.net/api/device?device_id=my-iot-device-01&code=<your-function-key>`
  - Replace `<your-function-app-name>` with your Function App name
  - Replace `<your-function-key>` with the key from Step 11
- No body needed

**Expected Response:**
- Status: `200 OK`
- Body: JSON array with temperature, humidity, pressure data from your device simulator

**Example response:**
```json
[
  {
    "id": "auto-generated-id",
    "deviceid": "my-iot-device-01",
    "temperature": 25.3,
    "humidity": 52.1,
    "pressure": 1013.2,
    "timestamp": 1705340123.456
  },
  {
    "id": "auto-generated-id-2",
    "deviceid": "my-iot-device-01",
    "temperature": 24.8,
    "humidity": 53.2,
    "pressure": 1012.8,
    "timestamp": 1705340133.789
  }
]
```

**If you get 404 or empty array:** Wait a few more minutes for data to flow through the pipeline, or check that your device simulator is still running.

#### 2. POST Create House

**Request:**
- Method: `POST`
- URL: `https://<your-function-app-name>.azurewebsites.net/api/house?code=<your-function-key>`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "id": "house-001",
  "name": "My Smart Home",
  "location": "London, UK"
}
```

**Expected Response:**
- Status: `201 Created`
- Body:
```json
{
  "message": "House entity created successfully"
}
```

#### 3. GET House Data

Test that the house was created successfully.

**Request:**
- Method: `GET`
- URL: `https://<your-function-app-name>.azurewebsites.net/api/house?house_id=house-001&code=<your-function-key>`

**Expected Response:**
- Status: `200 OK`
- Body:
```json
[
  {
    "id": "house-001",
    "houseid": "My Smart Home",
    "location": "London, UK"
  }
]
```

#### 4. POST Create Room

**Request:**
- Method: `POST`
- URL: `https://<your-function-app-name>.azurewebsites.net/api/rooms?code=<your-function-key>`
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
- URL: `https://<your-function-app-name>.azurewebsites.net/api/rooms?room_id=room-001&code=<your-function-key>`

**Expected Response:**
- Status: `200 OK`
- Body:
```json
[
  {
    "id": "room-001",
    "room_name": "Living Room",
    "house_id": "house-001",
    "location": "Ground Floor"
  }
]
```

**Congratulations!** You've successfully built and tested a complete serverless IoT platform with REST API endpoints.

---

## Part 6: (Optional) Deploy Frontend

If you want to visualize the data in a web interface, see [FRONTEND_DEPLOYMENT_SUMMARY.md](FRONTEND_DEPLOYMENT_SUMMARY.md) for instructions on deploying the included Vue.js frontend application.

---

## Troubleshooting

### No data in Cosmos DB (iot-data container)
- **Check device simulator:** Ensure `simple_mqtt_device_simulator.py` is still running
- **Verify Stream Analytics status:** In Azure Portal, check that the job status is "Running"
- **Check Stream Analytics metrics:** Look for input/output events in the Monitoring section
- **Review Stream Analytics errors:** Check the Activity log for any error messages
- **Verify IoT Hub is receiving data:** Use VS Code Azure IoT Hub extension to monitor built-in endpoint

### Function returns 500 Internal Server Error
- **Check Function logs:** Azure Portal → Your Function App → Log stream
- **Verify Cosmos DB credentials:** Ensure endpoint and key are correct in all three function files
- **Check container names:** Ensure `iot-data`, `house-data`, and `room-data` containers exist
- **Test Cosmos DB connection:** Use Data Explorer in Azure Portal to manually query containers

### Function returns 404 Not Found
- **Verify deployment:** Run `func azure functionapp list-functions $FUNCTION_APP_NAME`
- **Check URL format:** Ensure you're using `/api/device`, `/api/house`, or `/api/rooms`
- **Verify function key:** Make sure you're including `?code=<your-key>` in the URL

### Function returns 401 Unauthorized
- **Check function key:** Verify you're using the correct function key from App keys
- **Key format:** Ensure the key parameter is `?code=<key>` not `?key=<key>`

### Device simulator connection errors
- **Verify connection details:** Check that device_id, iot_hub_name, and sas_token are correct
- **Check SAS token expiration:** SAS tokens expire after a certain time (default: 1 hour). Generate a new one if needed
- **Verify IoT Hub hostname:** Should be `<iot-hub-name>.azure-devices.net`
- **Check port number:** Should be `8883` for secure MQTT (MQTTS)
- **Verify TLS settings:** Ensure the authentication lines are uncommented

### Stream Analytics job fails to start
- **Check input configuration:** Verify IoT Hub name and shared access policy
- **Check output configuration:** Verify Cosmos DB account name and key
- **Review query syntax:** Ensure the SQL query is correct (no syntax errors)
- **Check container name:** Verify `iot-data` container exists in Cosmos DB

### Device GET endpoint returns empty array
- **Wait for data:** It can take 2-3 minutes for data to flow through the entire pipeline
- **Check device_id:** Ensure the query parameter matches the device ID sending data
- **Verify Stream Analytics:** Check that the job is running and processing events
- **Check Cosmos DB:** Use Data Explorer to verify data exists in `iot-data` container

---

## Cleanup

**Important:** Delete all resources to avoid ongoing charges!

### Option 1: Delete Entire Resource Group (Recommended)

This deletes all resources at once: IoT Hub, Cosmos DB, Stream Analytics, Function App, and Storage Account.

```bash
az group delete --name resourceGroupIotPlatform --yes --no-wait
```

### Option 2: Delete Individual Resources

If you want to keep some resources, delete them individually:

**Stop Stream Analytics job first (required before deletion):**
```bash
az stream-analytics job stop \
  --name stream-iot-data \
  --resource-group resourceGroupIotPlatform
```

**Delete Stream Analytics job:**
```bash
az stream-analytics job delete \
  --name stream-iot-data \
  --resource-group resourceGroupIotPlatform \
  --yes
```

**Delete Function App:**
```bash
az functionapp delete \
  --name $FUNCTION_APP_NAME \
  --resource-group resourceGroupIotPlatform
```

**Delete Storage Account:**
```bash
az storage account delete \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group resourceGroupIotPlatform \
  --yes
```

**Delete Cosmos DB:**
```bash
az cosmosdb delete \
  --name $COSMOS_DB_ACCOUNT_NAME \
  --resource-group resourceGroupIotPlatform \
  --yes
```

**Delete IoT Hub:**
```bash
az iot hub delete \
  --name $IOT_HUB_NAME \
  --resource-group resourceGroupIotPlatform
```

---

## Summary and Learning Outcomes

Congratulations! You've built a complete serverless IoT platform. You learned:

✅ **IoT Hub**: Device connectivity and message ingestion with MQTT protocol
✅ **Stream Analytics**: Real-time data processing and SQL-based transformations
✅ **Cosmos DB**: NoSQL database with multiple containers and partition keys
✅ **Azure Functions**: Serverless REST API with HTTP triggers
✅ **End-to-end data flow**: Device → IoT Hub → Stream Analytics → Cosmos DB → Functions → API
✅ **REST API design**: GET and POST endpoints with query parameters and JSON bodies
✅ **Azure CLI**: Infrastructure provisioning and management
✅ **Python development**: Function deployment and dependency management

### Architecture Patterns You've Implemented

1. **Device-to-Cloud Telemetry**: IoT devices sending sensor data to the cloud
2. **Stream Processing**: Real-time data transformation and routing
3. **Serverless Computing**: Pay-per-execution functions without managing servers
4. **NoSQL Database**: Flexible schema for different data types (telemetry, houses, rooms)
5. **RESTful API**: Standard HTTP methods (GET, POST) for CRUD operations
6. **Microservices**: Independent functions handling different API endpoints

## Next Steps

- Explore the [example frontend](example-frontend/) to visualize your IoT data
- Modify the Stream Analytics query to add data aggregations or filtering
- Add more Azure Functions endpoints (e.g., DELETE operations, UPDATE operations)
- Implement proper authentication using Azure AD or API Management
- Add Azure Application Insights for monitoring, logging, and performance tracking
- Explore Azure Key Vault to securely store Cosmos DB keys
- Add data retention policies to automatically delete old telemetry
- Implement webhooks or alerts for specific sensor thresholds

---

## Reference Scripts

This directory includes automation scripts for reference:
- `azure-cli-iot-platform.sh`: Complete infrastructure setup script
- `azure-functions-cli.sh`: Function deployment helper script

**Note:** These scripts are for reference only. Following the manual steps above will help you understand each component better and troubleshoot any issues that arise. 
