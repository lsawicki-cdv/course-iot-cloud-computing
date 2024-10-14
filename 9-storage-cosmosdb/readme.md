# Azure CosmosDB

## Developing a Python app using the Azure Cosmos DB SQL API
Azure Cosmos DB is a globally distributed multi-model database. One of the supported APIs is the SQL API, which provides a JSON document model with SQL querying and JavaScript procedural logic. This sample shows you how to use Azure Cosmos DB with the SQL API to store and access data from a Node.js application.

## Tested environments
Ubuntu 22.04
Python 3.10.12

### Prerequisites
```
pip3 install pipenv==2023.8.28
```

### Project packages installation
```bash
pipenv install
```

## Run Azure CosmosDB sample
```bash
pipenv run python azure-cosmosdb-sample.py
```

## Change your Azure CosmosDB credentials
Change the Azure Cosmos DB endpoint URL and the key in the `config.py` file.

## More information

[**Azure CosmosDB Free Tier**](https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier)
- [Azure Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/introduction)
- [Azure Cosmos DB: SQL API](https://docs.microsoft.com/en-us/azure/cosmos-db/sql-api-introduction)