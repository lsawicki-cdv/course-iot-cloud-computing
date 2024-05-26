## Azure Functions - Bicep

Task: Deploy an Azure Function using Bicep

Deploy the Bicep file using either Azure CLI
```
az group create --name cloud-computing --location eastus
az deployment group create --resource-group cloud-computing --template-file main.bicep --parameters appInsightsLocation=<app-location>
```