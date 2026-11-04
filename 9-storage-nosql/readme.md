# Azure CosmosDB

> Using AWS instead? Follow the [AWS version of this exercise](aws/readme.md).

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Developing a Python app using the Azure Cosmos DB SQL API
Azure Cosmos DB is a globally distributed multi-model database. One of the supported APIs is the SQL API, which provides a JSON document model with SQL querying and JavaScript procedural logic. This sample shows you how to use Azure Cosmos DB with the SQL API to store and access data from a Python application.

## Tested environments
Ubuntu 24.04
Python 3.12.3

## Your Azure CosmosDB credentials
The sample reads the Azure Cosmos DB endpoint URL and the key from the `ACCOUNT_HOST` and `ACCOUNT_KEY` environment variables (see `config.py`), so the key is not written in the code. You set them in step 8.

## Exercise
1. Be sure that you have installed Python, Pip and VS Code
2. Clone the repository to your computer
3. Go to this directory in the terminal in VS Code (`9-storage-nosql`)
4. On **macOS/Linux** type in the terminal the following commands
   ```bash
      python3 -m venv .venv
      source .venv/bin/activate
   ```
5. On **Windows** type in the terminal the following commands
   ```powershell
      py -m venv .venv
      .venv\scripts\activate
   ```
6. Install dependencies: `pip install -r requirements.txt`
7. Issue the following commands in **the Azure Cloud Shell**

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables. The account name gets a random number, because it must be globally unique
   ```bash
      RESOURCE_GROUP="myResourceGroupCosmosDb"
   ```
   ```bash
      COSMOS_DB_ACCOUNT="my-cosmos-super-db-$RANDOM"
   ```
   ```bash
      LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
      az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a free tier CosmosDB account for NoSQL. It takes a few minutes. Only one account per subscription can use the free tier (1000 RU/s and 25 GB): if the command fails because the free tier is already used, delete your old Cosmos DB account first
   ```bash
      az cosmosdb create --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --locations regionName=$LOCATION --enable-free-tier true --default-consistency-level "Session"
   ```
   4. Get URL of the database and master key to get access. The output looks like `AccountEndpoint=https://<account>.documents.azure.com:443/;AccountKey=<key>;`
   ```bash
      az cosmosdb keys list --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --type connection-strings --query "connectionStrings[0].connectionString" --output tsv
   ```

   **Option B: Using PowerShell**
   1. Set the terminal environmental variables (PowerShell syntax). The account name gets a random number, because it must be globally unique
   ```powershell
      $RESOURCE_GROUP="myResourceGroupCosmosDb"
   ```
   ```powershell
      $COSMOS_DB_ACCOUNT="my-cosmos-super-db-$(Get-Random -Maximum 99999)"
   ```
   ```powershell
      $LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   2. Create a resource group using the terminal environmental variables
   ```powershell
      az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a free tier CosmosDB account for NoSQL. It takes a few minutes. Only one account per subscription can use the free tier (1000 RU/s and 25 GB): if the command fails because the free tier is already used, delete your old Cosmos DB account first
   ```powershell
      az cosmosdb create --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --locations regionName=$LOCATION --enable-free-tier true --default-consistency-level "Session"
   ```
   4. Get URL of the database and master key to get access. The output looks like `AccountEndpoint=https://<account>.documents.azure.com:443/;AccountKey=<key>;`
   ```powershell
      az cosmosdb keys list --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --type connection-strings --query "connectionStrings[0].connectionString" --output tsv
   ```
8. In the terminal on your computer, set the URL (`AccountEndpoint`) and the key (`AccountKey`) from the output of the previous command as environment variables

   On **macOS/Linux**:
   ```bash
   export ACCOUNT_HOST="https://<account>.documents.azure.com:443/"
   export ACCOUNT_KEY="<key>"
   ```
   On **Windows** (PowerShell):
   ```powershell
   $env:ACCOUNT_HOST="https://<account>.documents.azure.com:443/"
   $env:ACCOUNT_KEY="<key>"
   ```
9. Run the Python script from the `9-storage-nosql` directory: `python azure-cosmosdb-sample.py`. It creates the database `my-super-database` and the container `my-super-container` (400 RU/s, within the free tier) if they don't exist
10. Check if items were created: in the Azure Portal open your Cosmos DB account → **Data Explorer** → `my-super-database` → `my-super-container` → **Items**. Open an item to see its JSON, and compare the fields of a `SalesOrder` from `Account1` and one from `Account2`
11. Delete the resource group in the Azure Cloud Shell (the same command works in Bash and PowerShell)
   ```bash
   az group delete --name $RESOURCE_GROUP --yes --no-wait
   ```

## More information

[**Azure CosmosDB Free Tier**](https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier)
- [Azure Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/introduction)
- [Azure Cosmos DB: SQL API](https://docs.microsoft.com/en-us/azure/cosmos-db/sql-api-introduction)