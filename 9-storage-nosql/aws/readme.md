# Amazon DynamoDB

This is the AWS version of the [Azure Cosmos DB exercise](../readme.md).

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. DynamoDB is Free Tier eligible: 25 GB of storage and 25 read and 25 write capacity units in provisioned mode per region. The table in this exercise uses 5 of each. Delete the table at the end of the exercise.

## Developing a Python app using Amazon DynamoDB
Amazon DynamoDB is a serverless NoSQL database. Like Azure Cosmos DB for NoSQL, it stores items without a fixed schema: two items in the same table can have different fields. Every item has a primary key, and DynamoDB spreads the items across partitions by the partition key. This sample shows you how to use DynamoDB to store and access data from a Python application with the AWS SDK for Python (`boto3`). It does the same steps as the Azure sample: create, read, query, replace, upsert and delete items.

| Azure | AWS |
|-------|-----|
| Azure Cosmos DB account (globally unique name) | Nothing to create - DynamoDB is ready in every account and region |
| Database | No database level - tables belong to your account and region |
| Container | Table (the name must be unique only in your account and region) |
| Partition key `/partitionKey` + `id` | Primary key: partition key `partitionKey` + sort key `id` |
| Request Units (RU/s), free tier 1000 RU/s | Read and write capacity units (RCU/WCU), Free Tier 25 + 25 |
| URL and master key in `config.py` | No keys - AWS CloudShell is already signed in as you (IAM) |
| `azure-cosmos` SDK | `boto3` (AWS SDK for Python) |
| SQL query (`SELECT * FROM r WHERE ...`) | `query` (by partition key) and `scan` (whole table) - or PartiQL, a SQL-like language |
| `ttl` (seconds) on items | TTL turned on for the table, `ttl` holds the time of expiry (seconds since 1970) |
| Data Explorer in the Azure Portal | Explore items in the AWS Console |
| Resource group | No direct equivalent - the table is deleted on its own |

## Tested environments
Ubuntu 24.04
Python 3.9 (the version in AWS CloudShell) with `boto3` 1.42

## Exercise
1. Open **AWS CloudShell** (the terminal icon in the AWS Console's top bar). It already has Python 3 and `boto3`, and is signed in as you. Check the region in the top-right corner of the Console
2. Download the sample (the same in Bash and PowerShell; start PowerShell by typing `pwsh`)
   ```bash
   curl -o dynamodb_sample.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/9-storage-nosql/aws/dynamodb_sample.py
   ```
3. Issue the following commands in **AWS CloudShell**

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables
   ```bash
      REGION="eu-west-2"  # Change to another region if needed
   ```
   ```bash
      TABLE_NAME="my-super-table"
   ```
   2. Create a table with the partition key `partitionKey` and the sort key `id`, both strings (`S`). Provisioned mode with 5 read and 5 write capacity units stays in the Free Tier
   ```bash
      aws dynamodb create-table \
         --region $REGION \
         --table-name $TABLE_NAME \
         --attribute-definitions AttributeName=partitionKey,AttributeType=S AttributeName=id,AttributeType=S \
         --key-schema AttributeName=partitionKey,KeyType=HASH AttributeName=id,KeyType=RANGE \
         --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```
   3. Wait until the table is ready (about 20 seconds)
   ```bash
      aws dynamodb wait table-exists --region $REGION --table-name $TABLE_NAME
   ```
   4. Turn on Time to Live (TTL): DynamoDB deletes items after the time stored in their `ttl` field (the sample sets it to 30 days from now)
   ```bash
      aws dynamodb update-time-to-live --region $REGION --table-name $TABLE_NAME --time-to-live-specification Enabled=true,AttributeName=ttl
   ```

   **Option B: Using PowerShell**
   1. Set the terminal environmental variables (PowerShell syntax)
   ```powershell
      $REGION="eu-west-2"  # Change to another region if needed
   ```
   ```powershell
      $TABLE_NAME="my-super-table"
   ```
   2. Create a table with the partition key `partitionKey` and the sort key `id`, both strings (`S`). Provisioned mode with 5 read and 5 write capacity units stays in the Free Tier
   ```powershell
      aws dynamodb create-table `
         --region $REGION `
         --table-name $TABLE_NAME `
         --attribute-definitions AttributeName=partitionKey,AttributeType=S AttributeName=id,AttributeType=S `
         --key-schema AttributeName=partitionKey,KeyType=HASH AttributeName=id,KeyType=RANGE `
         --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```
   3. Wait until the table is ready (about 20 seconds)
   ```powershell
      aws dynamodb wait table-exists --region $REGION --table-name $TABLE_NAME
   ```
   4. Turn on Time to Live (TTL): DynamoDB deletes items after the time stored in their `ttl` field (the sample sets it to 30 days from now)
   ```powershell
      aws dynamodb update-time-to-live --region $REGION --table-name $TABLE_NAME --time-to-live-specification Enabled=true,AttributeName=ttl
   ```
4. Look at `dynamodb_sample.py` and compare it with `azure-cosmosdb-sample.py`:
   - There is no URL or key: `boto3` uses the identity CloudShell is signed in with
   - `get_item`, `query` and `delete_item` need the whole primary key or the partition key, as the Cosmos DB methods need the partition key
   - Numbers are stored as `Decimal`, because DynamoDB doesn't accept Python floats (`to_dynamodb`)
   - `put_item` replaces the whole item, or creates it if it doesn't exist. A `ConditionExpression` makes it create-only (`attribute_not_exists`) or replace-only (`attribute_exists`)
5. Run the sample. It uses the table `my-super-table` in the CloudShell region (`AWS_REGION`). To use another table, set `DYNAMODB_TABLE` first (Bash: `export DYNAMODB_TABLE=<name>`, PowerShell: `$env:DYNAMODB_TABLE="<name>"`)
   ```bash
   python3 dynamodb_sample.py
   ```
   If your CloudShell region is not the one with the table, set it for the sample first (Bash: `export AWS_REGION=$REGION`, PowerShell: `$env:AWS_REGION=$REGION`)
6. Check if items were created
   1. In the AWS Console: DynamoDB → Tables → `my-super-table` → **Explore table items**. Open an item to see its JSON, and compare the fields of a `SalesOrder` from `Account1` and one from `Account2`
   2. In CloudShell, read all items with a scan (the same in Bash and PowerShell)
   ```bash
   aws dynamodb scan --region $REGION --table-name $TABLE_NAME --query "Items[].[partitionKey.S,id.S,subtotal.N]" --output table
   ```
   3. Query the items of one partition with PartiQL, a SQL-like language for DynamoDB

   **Bash:**
   ```bash
   aws dynamodb execute-statement --region $REGION --statement "SELECT id, total_due FROM \"$TABLE_NAME\" WHERE partitionKey = 'Account2'"
   ```
   **PowerShell:**
   ```powershell
   aws dynamodb execute-statement --region $REGION --statement "SELECT id, total_due FROM `"$TABLE_NAME`" WHERE partitionKey = 'Account2'"
   ```
7. Delete the table (the same command works in Bash and PowerShell)
   ```bash
   aws dynamodb delete-table --region $REGION --table-name $TABLE_NAME
   ```

You can also run the sample on your computer: install `boto3` in a virtual environment (`pip install boto3`) and set up AWS credentials there (see [1-cloud-account/aws](../../1-cloud-account/aws/readme.md)).

## More information

- [Amazon DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html)
- [Core components of DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html)
- [Amazon DynamoDB pricing (Free Tier)](https://aws.amazon.com/dynamodb/pricing/)
- [PartiQL for DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ql-reference.html)
