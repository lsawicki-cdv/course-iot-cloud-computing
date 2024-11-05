#!/bin/bash

# Variables
RESOURCE_GROUP="myResourceGroupVMForDocker"
LOCATION="uksouth"
VM_NAME="my-vm-mqtt-docker"
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

# Install Docker engine on the VM
az vm extension set \
  --resource-group $RESOURCE_GROUP \
  --vm-name $VM_NAME \
  --name DockerExtension \
  --publisher Microsoft.Azure.Extensions \
  --version 1.0 \
  --settings '{"docker": {"port": "2375"}}'

# Create network security group rule
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${VM_NAME}NSG \
  --name allow-http \
  --protocol tcp \
  --priority 1020 \
  --destination-port-range 1883 \
  --access allow

# Access the VM
az ssh vm --resource-group $RESOURCE_GROUP --name $VM_NAME
