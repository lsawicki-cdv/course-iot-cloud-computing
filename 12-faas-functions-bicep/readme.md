## Azure Functions - Bicep

Task: Deploy an Azure Function using Bicep

Deploy the Bicep file using Azure CLI
```
az group create --name cloud-computing-faas --location uksouth
az deployment group create --resource-group cloud-computing-faas --template-file main.bicep --parameters appInsightsLocation=uksouth
```