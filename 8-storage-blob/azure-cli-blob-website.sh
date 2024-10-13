#!/bin/bash

# Variables
RESOURCE_GROUP_NAME="myResourceGroupWebsite"
STORAGE_ACCOUNT_NAME="mystorageaccount$RANDOM"
LOCATION="uksouth"

# Create a resource group
az group create --name $RESOURCE_GROUP_NAME --location $LOCATION

# Create a storage account
az storage account create --name $STORAGE_ACCOUNT_NAME --location $LOCATION --resource-group $RESOURCE_GROUP_NAME --sku Standard_LRS

# Enable static website hosting
az storage blob service-properties update --account-name $STORAGE_ACCOUNT_NAME --static-website --index-document index.html --404-document error.html

# Upload files to the $web container
az storage blob upload-batch --destination \$web --source ./website --account-name $STORAGE_ACCOUNT_NAME

# Get the static website URL
az storage account show --name $STORAGE_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --query "primaryEndpoints.web" --output tsv

# Delete a resource group
# az group delete --name $RESOURCE_GROUP_NAME --yes --no-wait