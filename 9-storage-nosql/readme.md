# Azure CosmosDB

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Developing a Python app using the Azure Cosmos DB SQL API
Azure Cosmos DB is a globally distributed multi-model database. One of the supported APIs is the SQL API, which provides a JSON document model with SQL querying and JavaScript procedural logic. This sample shows you how to use Azure Cosmos DB with the SQL API to store and access data from a Node.js application.

## Tested environments
Ubuntu 24.04
Python 3.12.3

## Change your Azure CosmosDB credentials
Change the Azure Cosmos DB endpoint URL and the key in the `config.py` file.

## Exercise
1. Be sure that you have installed Python, Pip and VS Code
2. Clone the repository to your computer
3. Go to this directory in the terminal in VS Code (`9-storage-cosmosdb`)
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
   1. Set the terminal environmental variables
   ```bash
      RESOURCE_GROUP="myResourceGroupCosmosDb"
   ```
   ```bash
      COSMOS_DB_ACCOUNT="my-cosmos-super-db"
   ```
   ```bash
      LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
      az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a free tier CosmosDB account for NoSQL
   ```bash
      az cosmosdb create --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --locations regionName=$LOCATION --enable-free-tier true --default-consistency-level "Session"
   ```
   4. Get URL of the database and master key to get access
   ```bash
      az cosmosdb keys list --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --type connection-strings --query "connectionStrings[0].connectionString" --output tsv
   ```

   **Option B: Using PowerShell**
   1. Set the terminal environmental variables (PowerShell syntax)
   ```powershell
      $RESOURCE_GROUP="myResourceGroupCosmosDb"
   ```
   ```powershell
      $COSMOS_DB_ACCOUNT="my-cosmos-super-db"
   ```
   ```powershell
      $LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   2. Create a resource group using the terminal environmental variables
   ```powershell
      az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a free tier CosmosDB account for NoSQL
   ```powershell
      az cosmosdb create --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --locations regionName=$LOCATION --enable-free-tier true --default-consistency-level "Session"
   ```
   4. Get URL of the database and master key to get access
   ```powershell
      az cosmosdb keys list --name $COSMOS_DB_ACCOUNT --resource-group $RESOURCE_GROUP --type connection-strings --query "connectionStrings[0].connectionString" --output tsv
   ```

   5. Based on the output from the previous command change properties in the `config.py`
8. Run the Python script from the `9-storage-cosmosdb` directory: `python azure-cosmosdb-sample.py`
9. Check if items where created.
10. Delete resource group

## More information

[**Azure CosmosDB Free Tier**](https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier)
- [Azure Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/introduction)
- [Azure Cosmos DB: SQL API](https://docs.microsoft.com/en-us/azure/cosmos-db/sql-api-introduction)