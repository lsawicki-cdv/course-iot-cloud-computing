#!/bin/bash

# Variables
RESOURCE_GROUP="myResourceGroupVM"
LOCATION="uksouth"
VM_NAME="my-vm"
IMAGE="Ubuntu2204"
SIZE="Standard_B1s"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a virtual machine
az vm create \
    --resource-group $RESOURCE_GROUP \
    --name $VM_NAME \
    --image $IMAGE \
    --size $SIZE \
    --admin-username azureuser \
    --generate-ssh-keys


# Install ngnix server
az vm extension set \
  --resource-group $RESOURCE_GROUP \
  --vm-name $VM_NAME \
  --name customScript \
  --publisher Microsoft.Azure.Extensions \
  --settings '{"fileUris":["https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh"]}' \
  --protected-settings '{"commandToExecute": "./vm.sh"}'    

# Get public IP address
IP_ADDRESS=$(az vm show \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --show-details \
  --query [publicIps] \
  --output tsv)

curl --connect-timeout 5 http://$IP_ADDRESS

# List network security group rules
az network nsg rule list \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${VM_NAME}NSG \
  --output table

# Create network security group rule
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${VM_NAME}NSG \
  --name allow-http \
  --protocol tcp \
  --priority 1020 \
  --destination-port-range 80 \
  --access allow

curl --connect-timeout 5 http://$IP_ADDRESS

# Delete a resource group
az group delete --name $RESOURCE_GROUP --yes --no-wait
