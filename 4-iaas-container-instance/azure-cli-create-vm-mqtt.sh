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

# List network security group rules
az network nsg rule list \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${VM_NAME}NSG \
  --output table

# Create network security group rule to allow TCP traffic on port 1883
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name ${VM_NAME}NSG \
  --name allow-mqtt \
  --protocol tcp \
  --priority 1020 \
  --destination-port-range 1883 \
  --access allow

# Install Docker engine on the VM
az vm extension set \
  --resource-group $RESOURCE_GROUP \
  --vm-name $VM_NAME \
  --name DockerExtension \
  --publisher Microsoft.Azure.Extensions \
  --version 1.0 \
  --settings '{"docker": {"port": "2375"}}'

# Install Azue CLI on the VM
az vm extension set \
  --resource-group $RESOURCE_GROUP \
  --vm-name $VM_NAME \
  --name customScript \
  --publisher Microsoft.Azure.Extensions \
  --settings '{"fileUris":["https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/4-iaas-container-instance/install-azure-cli.sh"]}' \
  --protected-settings '{"commandToExecute": "./install-azure-cli.sh"}'

  # Get public IP address
IP_ADDRESS=$(az vm show \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --show-details \
  --query [publicIps] \
  --output tsv)

# Open a SSH session to the VM
ssh azureuser@$IP_ADDRESS

# Delete a resource group
# az group delete --name $RESOURCE_GROUP --yes --no-wait