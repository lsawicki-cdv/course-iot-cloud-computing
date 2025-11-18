# Azure Functions Deployment with Bicep

In this exercise, you'll learn Infrastructure as Code (IaC) using **Bicep**, Azure's domain-specific language for deploying resources. You'll deploy a complete Azure Functions serverless environment including storage, compute, and monitoring.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## What is Bicep?

**Bicep** is a declarative language for deploying Azure resources. It's:
- **Simpler than ARM templates** - cleaner syntax, easier to read and write
- **Azure-native** - designed specifically for Azure (unlike Terraform which is multi-cloud)
- **Fully supported by Microsoft** - first-class Azure tooling integration
- **Transpiled to ARM** - Bicep compiles to ARM JSON templates behind the scenes

### Bicep vs Other IaC Tools

| Feature | Bicep | ARM Templates | Terraform |
|---------|-------|---------------|-----------|
| Syntax | Clean, concise | Verbose JSON | HCL (HashiCorp) |
| Cloud Support | Azure only | Azure only | Multi-cloud |
| Learning Curve | Easy | Moderate | Moderate |
| Azure Integration | Excellent | Excellent | Good |

## Architecture Overview

This Bicep template deploys the following resources:

```
Resource Group
  ├── Storage Account (blob storage for function code)
  ├── App Service Plan (Consumption Y1 - serverless)
  ├── Function App (Node.js runtime)
  └── Application Insights (monitoring & logging)
```

### What You'll Learn

- How to write and understand Bicep templates
- How to deploy Azure resources using Infrastructure as Code
- Azure Functions architecture and required components
- Bicep parameters, variables, and resource declarations
- Resource dependencies in Bicep

## Tested Environments

- Ubuntu 22.04/24.04
- Azure CLI 2.50+
- Bicep CLI (included with Azure CLI)

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- Azure CLI installed and logged in
- Basic understanding of Azure Functions (complete Exercise 10 first)

---

## Part 1: Understand the Bicep Template

### Step 1: Examine the Bicep File

Open `main.bicep` and review its structure. Let's break down the key components:

**Parameters** (lines 1-24):
```bicep
param appName string = 'fnapp${uniqueString(resourceGroup().id)}'
param storageAccountType string = 'Standard_LRS'
param location string = resourceGroup().location
param appInsightsLocation string
param runtime string = 'node'
```

- `appName`: Function app name (auto-generated with unique suffix)
- `storageAccountType`: Storage redundancy level (LRS = locally redundant)
- `location`: Inherits from resource group location
- `appInsightsLocation`: Must be specified (not all regions support App Insights)
- `runtime`: Programming language runtime (node, dotnet, or java)

**Variables** (lines 26-30):
```bicep
var functionAppName = appName
var hostingPlanName = appName
var applicationInsightsName = appName
var storageAccountName = '${uniqueString(resourceGroup().id)}azfunctions'
```

Variables derive names for all resources from the base `appName` parameter.

**Resources** (lines 32-110):

1. **Storage Account** (lines 32-43): Required for Azure Functions to store code and state
2. **App Service Plan** (lines 45-53): Consumption plan (Y1 SKU) for serverless execution
3. **Function App** (lines 55-100): The actual Functions app with configuration
4. **Application Insights** (lines 102-110): Monitoring and telemetry

**Key Bicep Concepts Demonstrated:**

- **Resource dependencies**: Function App depends on Storage Account (implicit via reference)
- **`uniqueString()` function**: Generates unique names to avoid conflicts
- **`listKeys()` function**: Securely retrieves storage account keys at deployment time
- **`@allowed` decorator**: Restricts parameter values to valid options

---

## Part 2: Deploy with Bicep

### Step 2: Create Resource Group

Open **Azure Cloud Shell** from the Azure Portal.

**Option A: Using Bash (recommended)**

**Set the resource group name:**

```bash
RESOURCE_GROUP="cloud-computing-faas"
```

Set the Azure region (change if needed):

```bash
LOCATION="uksouth"
```

Set the App Insights region (same as location or closest available):

```bash
APP_INSIGHTS_LOCATION="uksouth"
```

**Create the resource group:**

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Option B: Using PowerShell**

**Set the resource group name:**

```powershell
$RESOURCE_GROUP="cloud-computing-faas"
```

Set the Azure region (change if needed):

```powershell
$LOCATION="uksouth"
```

Set the App Insights region (same as location or closest available):

```powershell
$APP_INSIGHTS_LOCATION="uksouth"
```

**Create the resource group:**

```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 3: Deploy the Bicep Template

**Option A: Using Bash (recommended)**

**Deploy using Azure CLI:**

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters appInsightsLocation=$APP_INSIGHTS_LOCATION
```

**Option B: Using PowerShell**

**Deploy using Azure CLI:**

```powershell
az deployment group create `
  --resource-group $RESOURCE_GROUP `
  --template-file main.bicep `
  --parameters appInsightsLocation=$APP_INSIGHTS_LOCATION
```

This command:
1. Validates the Bicep template
2. Transpiles Bicep to ARM JSON
3. Deploys resources to Azure
4. Shows progress and any errors

**Wait 2-3 minutes for deployment to complete**. You'll see output like:

```json
{
  "id": "/subscriptions/.../resourceGroups/cloud-computing-faas/providers/Microsoft.Resources/deployments/main",
  "location": null,
  "name": "main",
  "properties": {
    "correlationId": "...",
    "mode": "Incremental",
    "provisioningState": "Succeeded",
    ...
  }
}
```

**Important**: Look for `"provisioningState": "Succeeded"` to confirm successful deployment.

### Step 4: Verify Deployment

**Option A: Using Bash (recommended)**

**List deployed resources:**

```bash
az resource list --resource-group $RESOURCE_GROUP --output table
```

You should see 4 resources:
- Storage account (e.g., `abc123azfunctions`)
- App Service Plan (e.g., `fnappdef456`)
- Function App (e.g., `fnappdef456`)
- Application Insights (e.g., `fnappdef456`)

**Get Function App URL:**

```bash
az functionapp show \
  --resource-group $RESOURCE_GROUP \
  --name $(az functionapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv) \
  --query "defaultHostName" \
  --output tsv
```

**Option B: Using PowerShell**

**List deployed resources:**

```powershell
az resource list --resource-group $RESOURCE_GROUP --output table
```

You should see 4 resources:
- Storage account (e.g., `abc123azfunctions`)
- App Service Plan (e.g., `fnappdef456`)
- Function App (e.g., `fnappdef456`)
- Application Insights (e.g., `fnappdef456`)

**Get Function App URL:**

```powershell
az functionapp show `
  --resource-group $RESOURCE_GROUP `
  --name $(az functionapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv) `
  --query "defaultHostName" `
  --output tsv
```

Save this URL - you'll use it to access your functions.

---

## Part 3: Deploy a Function to Your App

Your Function App infrastructure is ready, but it has no functions yet. Let's deploy a simple HTTP-triggered function.

### Step 5: Create a Simple Function Locally

**On your local machine**, create a new directory for your function:

```bash
mkdir my-bicep-function
cd my-bicep-function
```

**Initialize a Node.js Function App:**

```bash
func init --worker-runtime node --language javascript
```

**Create an HTTP trigger function:**

```bash
func new --name HttpExample --template "HTTP trigger" --authlevel "anonymous"
```

This creates a simple HTTP endpoint at `/api/HttpExample`.

### Step 6: Test Locally (Optional)

**Start the local Functions runtime:**

```bash
func start
```

**Test in another terminal:**

```bash
curl http://localhost:7071/api/HttpExample?name=Azure
```

You should see: `Hello, Azure. This HTTP triggered function executed successfully.`

Press **Ctrl+C** to stop the local runtime.

### Step 7: Deploy Function to Azure

**Option A: Using Bash (recommended)**

**Get your Function App name:**

```bash
FUNCTION_APP_NAME=$(az functionapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "Deploying to: $FUNCTION_APP_NAME"
```

**Deploy your function:**

```bash
func azure functionapp publish $FUNCTION_APP_NAME
```

**Option B: Using PowerShell**

**Get your Function App name:**

```powershell
$FUNCTION_APP_NAME=$(az functionapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
echo "Deploying to: $FUNCTION_APP_NAME"
```

**Deploy your function:**

```powershell
func azure functionapp publish $FUNCTION_APP_NAME
```

Wait 1-2 minutes. You'll see output showing the deployment progress and function URLs.

### Step 8: Test Your Deployed Function

**Option A: Using Bash (recommended)**

**Get the function URL:**

```bash
FUNCTION_URL="https://$(az functionapp show --resource-group $RESOURCE_GROUP --name $FUNCTION_APP_NAME --query 'defaultHostName' -o tsv)/api/HttpExample"
echo "Function URL: $FUNCTION_URL"
```

**Test the function:**

```bash
curl "$FUNCTION_URL?name=Bicep"
```

**Option B: Using PowerShell**

**Get the function URL:**

```powershell
$FUNCTION_URL="https://$(az functionapp show --resource-group $RESOURCE_GROUP --name $FUNCTION_APP_NAME --query 'defaultHostName' -o tsv)/api/HttpExample"
echo "Function URL: $FUNCTION_URL"
```

**Test the function:**

```powershell
curl "$FUNCTION_URL?name=Bicep"
```

**Expected response:**

```
Hello, Bicep. This HTTP triggered function executed successfully.
```

**Congratulations!** You've deployed Azure infrastructure using Bicep and deployed a function to it.

---

## Part 4: Understanding the Deployment

### Step 9: Explore What Was Created

**View the deployment in Azure Portal:**

1. Navigate to your resource group: `cloud-computing-faas`
2. Click **Deployments** in the left menu
3. Click on the deployment named `main`
4. Review the **Template** tab to see the generated ARM JSON
5. Review the **Outputs** tab (if any outputs were defined)

**Check Application Insights:**

1. Navigate to your Function App in the portal
2. Click **Application Insights** in the left menu
3. Explore logs, performance metrics, and live metrics

**View Function App configuration:**

1. Navigate to your Function App
2. Click **Configuration** under Settings
3. Review the Application Settings created by Bicep:
   - `AzureWebJobsStorage` - connection to storage account
   - `APPINSIGHTS_INSTRUMENTATIONKEY` - monitoring integration
   - `FUNCTIONS_WORKER_RUNTIME` - set to `node`

---

## Bicep Best Practices

### Modularization

For larger projects, split Bicep into modules:

```bicep
module storage 'modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    storageAccountName: storageAccountName
    location: location
  }
}
```

### Parameter Files

Create separate parameter files for different environments:

**dev.parameters.json:**

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "runtime": {
      "value": "node"
    },
    "appInsightsLocation": {
      "value": "uksouth"
    }
  }
}
```

Deploy with:

**Using Bash:**

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters dev.parameters.json
```

**Using PowerShell:**

```powershell
az deployment group create `
  --resource-group $RESOURCE_GROUP `
  --template-file main.bicep `
  --parameters dev.parameters.json
```

### Outputs

Add outputs to retrieve deployed resource information:

```bicep
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
```

---

## Troubleshooting

### Deployment fails with "InvalidTemplate" error

- **Check Bicep syntax**: Run `az bicep build --file main.bicep` to validate
- **Review error message**: Azure CLI shows specific line numbers and issues
- **Check parameter values**: Ensure all required parameters are provided

### Deployment fails with "Location not available" error

- **Check region availability**: Not all regions support all resource types
- **Try different region**: Use `az account list-locations -o table` to see available regions
- **Check App Insights location**: App Insights may not be available in your resource group region

### Function App created but deployment fails

- **Check Azure Functions Core Tools**: Ensure it's installed (`func --version`)
- **Check runtime version**: Ensure local runtime matches Azure configuration
- **Review deployment logs**: Use `func azure functionapp publish $FUNCTION_APP_NAME --verbose`

### "Cannot find storage account" during deployment

- **Check resource dependencies**: Ensure storage account is created before Function App
- **Wait and retry**: Sometimes Azure needs a moment; retry the deployment

### Function returns 500 error when invoked

- **Check Application Insights logs**: Navigate to App Insights → Logs
- **Review Function App logs**: Portal → Function App → Log Stream
- **Check code errors**: Review your function's `index.js` file for syntax errors

---

## Cleanup

**Important:** Delete all resources to avoid ongoing charges!

### Option 1: Delete Resource Group (Recommended)

This deletes all resources created by the Bicep template:

```bash
az group delete --name cloud-computing-faas --yes --no-wait
```

### Option 2: Delete Individual Resources

If you want to keep the resource group:

**Using Bash:**

```bash
# Get Function App name
FUNCTION_APP_NAME=$(az functionapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)

# Delete Function App
az functionapp delete --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP

# Get and delete App Service Plan
PLAN_NAME=$(az appservice plan list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az appservice plan delete --name $PLAN_NAME --resource-group $RESOURCE_GROUP --yes

# Get and delete Storage Account
STORAGE_NAME=$(az storage account list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az storage account delete --name $STORAGE_NAME --resource-group $RESOURCE_GROUP --yes

# Get and delete Application Insights
APP_INSIGHTS_NAME=$(az monitor app-insights component list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az monitor app-insights component delete --app $APP_INSIGHTS_NAME --resource-group $RESOURCE_GROUP
```

**Using PowerShell:**

```powershell
# Get Function App name
$FUNCTION_APP_NAME=$(az functionapp list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)

# Delete Function App
az functionapp delete --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP

# Get and delete App Service Plan
$PLAN_NAME=$(az appservice plan list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az appservice plan delete --name $PLAN_NAME --resource-group $RESOURCE_GROUP --yes

# Get and delete Storage Account
$STORAGE_NAME=$(az storage account list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az storage account delete --name $STORAGE_NAME --resource-group $RESOURCE_GROUP --yes

# Get and delete Application Insights
$APP_INSIGHTS_NAME=$(az monitor app-insights component list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az monitor app-insights component delete --app $APP_INSIGHTS_NAME --resource-group $RESOURCE_GROUP
```

---

## Summary and Learning Outcomes

Congratulations! You've successfully deployed Azure Functions using Infrastructure as Code. You learned:

✅ **Bicep Fundamentals**: Parameters, variables, resources, and functions
✅ **IaC Benefits**: Repeatable, version-controlled, automated deployments
✅ **Azure Functions Architecture**: Storage, compute plan, app, and monitoring components
✅ **Resource Dependencies**: How Bicep manages deployment order automatically
✅ **Azure CLI**: Deploying Bicep templates and managing resources
✅ **Function Deployment**: Publishing code to Azure-managed infrastructure
✅ **Monitoring**: Application Insights integration for observability

### Why Infrastructure as Code?

**Traditional Approach (Manual):**
- Click through Azure Portal (time-consuming)
- Hard to replicate exactly
- No version history
- Difficult to share with team
- Error-prone

**IaC Approach (Bicep):**
- ✅ Define infrastructure in code
- ✅ Version control with Git
- ✅ Deploy multiple environments consistently
- ✅ Easy to review and collaborate
- ✅ Automated and repeatable

### Bicep vs ARM Templates

The same deployment in ARM JSON would be ~150 lines. Bicep achieves it in ~110 lines with much better readability.

**ARM Template (verbose):**

```json
{
  "type": "Microsoft.Storage/storageAccounts",
  "apiVersion": "2022-05-01",
  "name": "[variables('storageAccountName')]",
  "location": "[parameters('location')]",
  "sku": {
    "name": "[parameters('storageAccountType')]"
  }
}
```

**Bicep (concise):**

```bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2022-05-01' = {
  name: storageAccountName
  location: location
  sku: { name: storageAccountType }
}
```

## Optional Next Steps

- Explore the Bicep file and modify parameters (try changing runtime to 'dotnet' or 'java')
- Add outputs to the Bicep file to display Function App URL after deployment
- Create a parameter file for different environments (dev, staging, production)
- Split the template into modules (storage module, function module, monitoring module)
- Compare this exercise with Exercise 14 (Terraform) to understand different IaC approaches
- Deploy a more complex function (with dependencies like Cosmos DB or Storage)
- Implement CI/CD pipeline using GitHub Actions or Azure DevOps to deploy Bicep automatically

## Additional Resources

- [Bicep Documentation](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)
- [Bicep Playground](https://aka.ms/bicepdemo) - Try Bicep in your browser
- [Azure Functions Bicep Reference](https://docs.microsoft.com/azure/templates/microsoft.web/sites)
- [Bicep Best Practices](https://docs.microsoft.com/azure/azure-resource-manager/bicep/best-practices)

---

## Reference Commands

**Option A: Using Bash (recommended)**

**Validate Bicep template:**

```bash
az bicep build --file main.bicep
```

**Preview changes before deployment (What-If):**

```bash
az deployment group what-if \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters appInsightsLocation=$APP_INSIGHTS_LOCATION
```

**View deployment logs:**

```bash
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.error
```

**Export existing resources to Bicep:**

```bash
az bicep decompile --file existing-template.json
```

**Option B: Using PowerShell**

**Validate Bicep template:**

```powershell
az bicep build --file main.bicep
```

**Preview changes before deployment (What-If):**

```powershell
az deployment group what-if `
  --resource-group $RESOURCE_GROUP `
  --template-file main.bicep `
  --parameters appInsightsLocation=$APP_INSIGHTS_LOCATION
```

**View deployment logs:**

```powershell
az deployment group show `
  --resource-group $RESOURCE_GROUP `
  --name main `
  --query properties.error
```

**Export existing resources to Bicep:**

```powershell
az bicep decompile --file existing-template.json
```