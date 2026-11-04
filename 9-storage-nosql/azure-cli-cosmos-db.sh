#!/bin/bash

# Variables
RESOURCE_GROUP="myResourceGroupCosmosDb"
COSMOS_DB_ACCOUNT="my-cosmos-super-db"
DATABASE_NAME="my-super-database"
CONTAINER_NAME="my-super-container"
LOCATION="uksouth"

# Create a resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create a free tier account for API for NoSQL
az cosmosdb create --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --locations regionName=$LOCATION --enable-free-tier true --default-consistency-level "Session"

# Create a database with shared throughput
az cosmosdb sql database create --account-name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --name $DATABASE_NAME --throughput 400

# Create container in the database
az cosmosdb sql container create --account-name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --database-name $DATABASE_NAME --name $CONTAINER_NAME --partition-key-path /myPartitionKey --throughput 400

# Get the URL and master key
az cosmosdb keys list --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --type connection-strings --query "connectionStrings[0].connectionString" --output tsv
