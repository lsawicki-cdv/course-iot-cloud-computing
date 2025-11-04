## Azure Functions - Bicep

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

Task: Deploy an Azure Function using Bicep

Deploy the Bicep file using Azure CLI
```bash
az group create --name cloud-computing-faas --location uksouth  # Change to your allowed region if needed
az deployment group create --resource-group cloud-computing-faas --template-file main.bicep --parameters appInsightsLocation=uksouth  # Change to your allowed region if needed
```