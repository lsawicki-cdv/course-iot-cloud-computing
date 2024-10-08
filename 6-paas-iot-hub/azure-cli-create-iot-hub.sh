#!/bin/bash

# Variables
RESOURCE_GROUP="myIotHubResourceGroup"
LOCATION="uksouth"
IOT_HUB_NAME="my-super-iot-hub"
IOT_DEVICE_NAME="my-new-device"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create an IoT Hub
az iot hub create --resource-group $RESOURCE_GROUP --name $IOT_HUB_NAME --location $LOCATION --sku F1 --partition-count 2

# Create a device identity
az iot hub device-identity create --hub-name $IOT_HUB_NAME --device-id $IOT_DEVICE_NAME

# Get SAS token for the IoT Hub
az iot hub generate-sas-token --hub-name $IOT_HUB_NAME --device-id $IOT_DEVICE_NAME --output table

# Delete a resource group
# az group delete --name $RESOURCE_GROUP --yes --no-wait