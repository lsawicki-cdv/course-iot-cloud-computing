#!/bin/bash

# Variables
REGION="eu-west-2"
TABLE_NAME="my-super-table"

# Create a table with the partition key "partitionKey" and the sort key "id" (Free Tier: provisioned mode)
aws dynamodb create-table \
  --region $REGION \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=partitionKey,AttributeType=S AttributeName=id,AttributeType=S \
  --key-schema AttributeName=partitionKey,KeyType=HASH AttributeName=id,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

aws dynamodb wait table-exists --region $REGION --table-name $TABLE_NAME

# Turn on Time to Live for the "ttl" field
aws dynamodb update-time-to-live --region $REGION --table-name $TABLE_NAME --time-to-live-specification Enabled=true,AttributeName=ttl

# Run the sample
AWS_REGION=$REGION DYNAMODB_TABLE=$TABLE_NAME python3 dynamodb_sample.py

# Read all items
aws dynamodb scan --region $REGION --table-name $TABLE_NAME --query "Items[].[partitionKey.S,id.S,subtotal.N]" --output table

# Delete the table
# aws dynamodb delete-table --region $REGION --table-name $TABLE_NAME
