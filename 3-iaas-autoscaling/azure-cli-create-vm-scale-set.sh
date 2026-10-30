#!/bin/bash

# Variables
RESOURCE_GROUP="myResourceGroupScaleSet2"
LOCATION="uksouth"
SCALE_SET_NAME="myScaleSet2"
IMAGE="Ubuntu2204"
SIZE="Standard_B1s"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a Virtual Machine Scale Set with fixed size
az vmss create \
  --resource-group $RESOURCE_GROUP \
  --name $SCALE_SET_NAME \
  --image $IMAGE \
  --upgrade-policy-mode automatic \
  --admin-username azureuser \
  --generate-ssh-keys \
  --instance-count 2 \
  --vm-sku $SIZE

# Install ngnix server
az vmss extension set \
  --resource-group $RESOURCE_GROUP \
  --vmss-name $SCALE_SET_NAME \
  --name customScript \
  --publisher Microsoft.Azure.Extensions \
  --settings '{"fileUris":["https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh"]}' \
  --protected-settings '{"commandToExecute": "./vm.sh"}'

# List network security group rules
az network nsg rule list \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${SCALE_SET_NAME}NSG \
  --output table

# Create network security group rule
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${SCALE_SET_NAME}NSG \
  --name allow-http \
  --protocol tcp \
  --priority 1020 \
  --destination-port-range 80 \
  --access allow

# Get public IP address of the azure load balancer
IP_ADDRESS=$(az network public-ip show \
  --resource-group $RESOURCE_GROUP \
  --name ${SCALE_SET_NAME}LBPublicIP \
  --query [ipAddress] \
  --output tsv)

curl --connect-timeout 5 http://$IP_ADDRESS

