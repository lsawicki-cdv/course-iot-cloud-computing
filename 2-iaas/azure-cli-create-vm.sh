#!/bin/bash

# Variables
RESOURCE_GROUP="myResourceGroup"
LOCATION="westeurope"
VM_NAME="myVM"
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
