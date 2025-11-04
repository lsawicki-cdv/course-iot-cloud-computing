#!/bin/bash

# Azure Static Web Apps Deployment Script for IoT Platform Frontend
# This script deploys the Vue.js frontend to Azure Static Web Apps

# Variables
RESOURCE_GROUP="resourceGroupIotPlatform"
LOCATION="westeurope"
STATIC_WEB_APP_NAME="cdv-iot-platform-frontend"
FRONTEND_DIR="./example-frontend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Azure Static Web Apps Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Please install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
echo -e "${YELLOW}Checking Azure login status...${NC}"
az account show &> /dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

# Check if resource group exists
echo -e "${YELLOW}Checking if resource group exists...${NC}"
if az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo -e "${GREEN}Resource group '$RESOURCE_GROUP' found${NC}"
else
    echo -e "${YELLOW}Resource group '$RESOURCE_GROUP' not found. Creating...${NC}"
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo -e "${GREEN}Resource group created${NC}"
fi

# Create Azure Static Web App
echo -e "${YELLOW}Creating Azure Static Web App...${NC}"
az staticwebapp create \
    --name $STATIC_WEB_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Free

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Static Web App created successfully${NC}"
else
    echo -e "${RED}Error creating Static Web App${NC}"
    exit 1
fi

# Get the deployment token
echo -e "${YELLOW}Retrieving deployment token...${NC}"
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name $STATIC_WEB_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "properties.apiKey" -o tsv)

# Get the Static Web App URL
STATIC_WEB_APP_URL=$(az staticwebapp show \
    --name $STATIC_WEB_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "defaultHostname" -o tsv)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Information${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Static Web App Name: ${YELLOW}$STATIC_WEB_APP_NAME${NC}"
echo -e "Resource Group: ${YELLOW}$RESOURCE_GROUP${NC}"
echo -e "URL: ${YELLOW}https://$STATIC_WEB_APP_URL${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Navigate to the frontend directory:"
echo -e "   ${GREEN}cd $FRONTEND_DIR${NC}"
echo -e ""
echo -e "2. Create a .env file with your Azure Functions configuration:"
echo -e "   ${GREEN}cp .env.example .env${NC}"
echo -e ""
echo -e "3. Edit .env and add your Azure Functions URL and key:"
echo -e "   ${GREEN}nano .env${NC}"
echo -e ""
echo -e "4. Install dependencies:"
echo -e "   ${GREEN}npm install${NC}"
echo -e ""
echo -e "5. Build the application:"
echo -e "   ${GREEN}npm run build${NC}"
echo -e ""
echo -e "6. Deploy using Azure Static Web Apps CLI:"
echo -e "   ${GREEN}npm install -g @azure/static-web-apps-cli${NC}"
echo -e "   ${GREEN}swa deploy ./dist --deployment-token '$DEPLOYMENT_TOKEN'${NC}"
echo -e ""
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Alternative: GitHub Actions Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "For automated deployments, connect your GitHub repository:"
echo -e "1. Go to: https://portal.azure.com"
echo -e "2. Navigate to: $STATIC_WEB_APP_NAME"
echo -e "3. Click 'GitHub Actions' and connect your repository"
echo -e ""
echo -e "${GREEN}Deployment script completed!${NC}"
