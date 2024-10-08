#!/bin/bash

# Variables
RESOURCE_GROUP="container-test"
ACI_NAME="mycontainertest"
ACI_IMAGE="my-custom-app:1.0.0"
LOCATION="eastus"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a container registry
az acr create --resource-group $RESOURCE_GROUP --name $ACI_NAME --sku Basic

# Log in to the container registry
az acr login --name $ACI_NAME

# Push the Docker image to the container registry
docker tag $ACI_IMAGE $ACI_NAME.azurecr.io/$ACI_IMAGE
docker push $ACI_NAME.azurecr.io/$ACI_IMAGE

# Create a container instance from the Docker image
az acr update -n $ACI_NAME --admin-enabled true
REGISTRY_USERNAME=$(az acr credential show --name $ACI_NAME --query username --output tsv)
REGISTRY_PASSWORD=$(az acr credential show --name $ACI_NAME --query passwords[0].value --output tsv)
az container create --resource-group $RESOURCE_GROUP --name $ACI_NAME --image $ACI_NAME.azurecr.io/$ACI_IMAGE --cpu 1 --memory 1 --registry-login-server $ACI_NAME.azurecr.io --registry-username $REGISTRY_USERNAME --registry-password $REGISTRY_PASSWORD --dns-name-label $ACI_NAME --ports 80

# Get the public IP address of the container instance
ACI_IP_ADDRESS=$(az container show --resource-group $RESOURCE_GROUP --name $ACI_NAME --query ipAddress.ip --output tsv)

# Test the container instance
curl --connect-timeout 5 http://$ACI_IP_ADDRESS
