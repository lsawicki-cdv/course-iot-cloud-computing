#!/bin/bash

# Variables
RESOURCE_GROUP="myResourceGroupPostgreSQL"
LOCATION="uksouth"
SERVER_NAME="iot-postgres-$RANDOM"
ADMIN_USER="iotadmin"
ADMIN_PASSWORD="<your-password>"
DATABASE_NAME="iotdata"
MY_IP="<your-public-ip>"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a PostgreSQL flexible server (Burstable B1ms, 32 GB) with public access from Azure services (e.g. Cloud Shell)
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $SERVER_NAME \
  --location $LOCATION \
  --admin-user $ADMIN_USER \
  --admin-password "$ADMIN_PASSWORD" \
  --tier Burstable \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0

# Allow connections from your computer
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --server-name $SERVER_NAME \
  --name allow-my-ip \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP

# Create a database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $SERVER_NAME \
  --name $DATABASE_NAME

# Connect with psql
psql "host=$SERVER_NAME.postgres.database.azure.com port=5432 dbname=$DATABASE_NAME user=$ADMIN_USER sslmode=require"

# Delete a resource group
# az group delete --name $RESOURCE_GROUP --yes --no-wait
