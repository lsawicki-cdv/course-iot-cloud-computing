#!/bin/bash

# Variables
RESOURCE_GROUP="container-test"
ACI_NAME="my-container-test"
ACI_IMAGE="mcr.microsoft.com/azuredocs/aci-helloworld"
LOCATION="eastus"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a container instance
az container create --resource-group $RESOURCE_GROUP --name $ACI_NAME --image $ACI_IMAGE --cpu 1 --memory 1.5 --dns-name-label $ACI_NAME --ports 80

# Output the FQDN of the container instance
az container show --resource-group $RESOURCE_GROUP --name $ACI_NAME --query "{FQDN:ipAddress.fqdn}" --output table