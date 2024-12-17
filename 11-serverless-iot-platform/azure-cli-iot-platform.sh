#!/bin/bash

# Variables
RESOURCE_GROUP="resourceGroupIotPlatform"
LOCATION="uksouth"
IOT_HUB_NAME="cdv-iot-platform-hub"
STREAM_ANALYTICS_JOB_NAME="stream-iot-data"
COSMOS_DB_ACCOUNT_NAME="cosmos-db-account-iot-platform"
COSMOS_DB_DATABASE_NAME="iot-platform-database"
FUNCTION_APP_NAME="cdv-iot-platform-functions"
STORAGE_ACCOUNT_NAME="cdviotplatformfunctions"
API_MANAGEMENT_NAME="cdv-iot-platform-api"
IOT_DEVICE_NAME="my-new-device-1"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create an IoT Hub
az iot hub create --resource-group $RESOURCE_GROUP --name $IOT_HUB_NAME --location $LOCATION --sku F1 --partition-count 2

# Create a device identity
az iot hub device-identity create --hub-name $IOT_HUB_NAME --device-id $IOT_DEVICE_NAME

# Get SAS token for the IoT Hub
az iot hub generate-sas-token --hub-name $IOT_HUB_NAME --device-id $IOT_DEVICE_NAME --output table

# TODO: Update and run MQTT device simulator from 6-paas-iot-hub

# Create a Cosmos DB account
az cosmosdb create --name $COSMOS_DB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --locations regionName=$LOCATION --enable-free-tier true --default-consistency-level "Session"

# Create a Cosmos DB database
az cosmosdb sql database create --account-name $COSMOS_DB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --name $COSMOS_DB_DATABASE_NAME --throughput 400

# Create a Cosmos DB container
az cosmosdb sql container create --account-name $COSMOS_DB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --database-name $COSMOS_DB_DATABASE_NAME --name "iot-data" --partition-key-path "/deviceid"

# Create a Stream Analytics job
az stream-analytics job create --resource-group $RESOURCE_GROUP --name $STREAM_ANALYTICS_JOB_NAME --location $LOCATION --output-error-policy Stop

# Get Connection string from IoT Hub
az iot hub show-connection-string --name $IOT_HUB_NAME --resource-group $RESOURCE_GROUP --query "connectionString"

### TODO: Add the SharedAccessKey and iotHubNamespace from IoT Hub to the Stream Analytics job
# Create an input for the Stream Analytics job
az stream-analytics input create --resource-group $RESOURCE_GROUP \
                                --job-name $STREAM_ANALYTICS_JOB_NAME --input-name cdviotplatformhub \
                                --properties "{\"type\":\"Stream\",\"datasource\":{\"type\" :\"Microsoft.Devices/IotHubs\",
                                \"properties\":{\"consumerGroupName\":\"\$Default\",\"endpoint\":\"messages/events\",\"iotHubNamespace\":\"cdv-iot-platform-hub\",
                                \"sharedAccessPolicyKey\":\"key=\",\"sharedAccessPolicyName\":\"iothubowner\"}},
                                \"serialization\":{\"type\":\"Json\",\"properties\":{\"encoding\":\"UTF8\"}}}"

# Get the input details
az stream-analytics input show --input-name $IOT_HUB_NAME --job-name $STREAM_ANALYTICS_JOB_NAME --resource-group $RESOURCE_GROUP

# Get Account Key from Cosmos DB
az cosmosdb keys list --name $COSMOS_DB_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --type keys --query "primaryMasterKey"

### TODO: Add the Account Key from Cosmos DB to the Stream Analytics job
# Create output for the Stream Analytics
az stream-analytics output create --resource-group $RESOURCE_GROUP \
                                --job-name $STREAM_ANALYTICS_JOB_NAME --output-name iotplatformdatabase --datasource "{\"type\":\"Microsoft.Storage/DocumentDB\",\"properties\":{\"accountId\":\"cosmos-db-account-iot-platform\",\"accountKey\":\"key==\",\"collectionNamePattern\":\"iot-data\",\"database\":\"iot-platform-database\"}}"

# Get the output details
az stream-analytics output show --output-name iotplatformdatabase --job-name $STREAM_ANALYTICS_JOB_NAME --resource-group $RESOURCE_GROUP

# TODO: Add query to the Stream Analytics job in the Azure portal
# "SELECT temperature, humidity, pressure, timestamp, device_id as deviceid INTO iotplatformdatabase FROM cdviotplatformhub PARTITION BY deviceid"

# Create a Storage Account for the Function App
az storage account create --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP --location $LOCATION --sku Standard_LRS

# Create a Function App for the IoT Platform API (Python)
az functionapp create --resource-group $RESOURCE_GROUP --consumption-plan-location $LOCATION --name $FUNCTION_APP_NAME --storage-account $STORAGE_ACCOUNT_NAME --runtime python --functions-version 4 --os-type Linux
