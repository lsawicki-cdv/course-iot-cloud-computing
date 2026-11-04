import datetime
import json
import os
import random
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# ----------------------------------------------------------------------------------------------------------
# Sample - demonstrates the basic CRUD operations on items in an Amazon DynamoDB table.
# It is the AWS version of azure-cosmosdb-sample.py and does the same steps in the same order.
# ----------------------------------------------------------------------------------------------------------

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'my-super-table')
REGION = os.environ.get('AWS_REGION')  # Set automatically in AWS CloudShell

# Items expire 30 days from now. In Cosmos DB "ttl" is a number of seconds; in DynamoDB it is
# the time of expiry in seconds since 1970 (epoch), and TTL must be turned on for the table.
TTL_SECONDS = 60 * 60 * 24 * 30


def to_dynamodb(item):
    # DynamoDB stores numbers as Decimal, and boto3 doesn't accept Python floats
    return json.loads(json.dumps(item), parse_float=Decimal)


def read_item(table, doc_id, account_number):
    print('\nReading Item by Id\n')

    # We can do an efficient point read lookup on the partition key and id (the whole primary key)
    response = table.get_item(Key={'partitionKey': account_number, 'id': doc_id})
    item = response['Item']

    print('Item read by Id {0}'.format(doc_id))
    print('Partition Key: {0}'.format(item.get('partitionKey')))
    print('Subtotal: {0}'.format(item.get('subtotal')))


def read_items(table):
    print('\nReading all items in a table\n')

    # A scan reads the whole table, one page (up to 1 MB) at a time. Scans of big tables are slow and
    # use a lot of read capacity, so use them rarely
    item_list = []
    response = table.scan(Limit=10)
    item_list.extend(response['Items'])
    while 'LastEvaluatedKey' in response:
        response = table.scan(Limit=10, ExclusiveStartKey=response['LastEvaluatedKey'])
        item_list.extend(response['Items'])

    print('Found {0} items'.format(len(item_list)))

    for doc in item_list:
        print('Item Id: {0}'.format(doc.get('id')))


def query_items(table, account_number):
    print('\nQuerying for an  Item by Partition Key\n')

    # A query always needs the partition key value, so it reads only one partition - efficient
    response = table.query(KeyConditionExpression=Key('partitionKey').eq(account_number))
    items = response['Items']

    print('Item queried by Partition Key {0}'.format(items[0].get('id')))


def replace_item(table, doc_id, account_number):
    print('\nReplace an Item\n')

    read_item = table.get_item(Key={'partitionKey': account_number, 'id': doc_id})['Item']
    read_item['subtotal'] = read_item['subtotal'] + 1
    # Replace only if the item exists (put_item alone would also create a new item)
    table.put_item(Item=read_item, ConditionExpression='attribute_exists(id)')

    print('Replaced Item\'s Id is {0}, new subtotal={1}'.format(
        read_item['id'], read_item['subtotal']))


def upsert_item(table, doc_id, account_number):
    print('\nUpserting an item\n')

    read_item = table.get_item(Key={'partitionKey': account_number, 'id': doc_id})['Item']
    read_item['subtotal'] = read_item['subtotal'] + 1
    # put_item creates the item, or replaces it if an item with the same key exists
    table.put_item(Item=read_item)

    print('Upserted Item\'s Id is {0}, new subtotal={1}'.format(
        read_item['id'], read_item['subtotal']))


def delete_item(table, doc_id, account_number):
    print('\nDeleting Item by Id\n')

    table.delete_item(Key={'partitionKey': account_number, 'id': doc_id})

    print('Deleted item\'s Id is {0}'.format(doc_id))


def get_sales_order(item_id):
    order1 = {'id': item_id,
              'partitionKey': 'Account1',
              'purchase_order_number': 'PO18009186470',
              'order_date': datetime.date(2005, 1, 10).strftime('%c'),
              'subtotal': 419.4589,
              'tax_amount': 12.5838,
              'freight': 472.3108,
              'total_due': 985.018,
              'items': [
                  {'order_qty': 1,
                   'product_id': 100,
                   'unit_price': 418.4589,
                   'line_price': 418.4589
                   }
              ],
              'ttl': int(time.time()) + TTL_SECONDS
              }

    return to_dynamodb(order1)


def get_sales_order_v2(item_id):
    # notice new fields have been added to the sales order
    order2 = {'id': item_id,
              'partitionKey': 'Account2',
              'purchase_order_number': 'PO15428132599',
              'order_date': datetime.date(2005, 7, 11).strftime('%c'),
              'due_date': datetime.date(2005, 7, 21).strftime('%c'),
              'shipped_date': datetime.date(2005, 7, 15).strftime('%c'),
              'subtotal': 6107.0820,
              'tax_amount': 586.1203,
              'freight': 183.1626,
              'discount_amt': 1982.872,
              'total_due': 4893.3929,
              'items': [
                  {'order_qty': 3,
                   # notice how in item details we no longer reference a ProductId
                   'product_code': 'A-123',
                   # instead we have decided to denormalise our schema and include
                   'product_name': 'Product 1',
                   # the Product details relevant to the Order on to the Order directly
                   'currency_symbol': '$',
                   # this is a typical refactor that happens in the course of an application
                   'currency_code': 'USD',
                   # that would have previously required schema changes and data migrations etc.
                   'unit_price': 17.1,
                   'line_price': 5.7
                   }
              ],
              'ttl': int(time.time()) + TTL_SECONDS
              }

    return to_dynamodb(order2)


def create_items(table):
    print('\nCreating Items\n')

    # Create a SalesOrder object. This object has nested properties and various types including numbers, dates and strings.
    # This can be saved as is without converting into rows/columns.
    sales_order_id = 'SalesOrder1'
    sales_order = get_sales_order(sales_order_id)
    try:
        # Create only if no item with this key exists yet
        table.put_item(Item=sales_order, ConditionExpression='attribute_not_exists(id)')

    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            raise
        print(f"Sales order with id {sales_order_id} was found")
        delete_item(table, sales_order_id, 'Account1')
        table.put_item(Item=sales_order)

    # As your app evolves, let's say your object has a new schema. You can insert SalesOrderV2 objects without any
    # changes to the database tier.
    # Generate a random sales order ID
    sales_order_id = f"SalesOrder{random.randint(2, 99999)}"
    print(f"Creating a sales order with ID {sales_order_id}")
    sales_order2 = get_sales_order_v2(sales_order_id)
    table.put_item(Item=sales_order2)

    # As your app evolves, let's say your object has a new schema. You can insert SalesOrderV2 objects without any
    # changes to the database tier.
    sales_order_id = f"SalesOrder{random.randint(2, 99999)}"
    print(f"Creating a sales order with ID {sales_order_id}")
    sales_order3 = get_sales_order(sales_order_id)
    table.put_item(Item=sales_order3)


def run_sample():
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    try:
        # setup the table for this sample. In DynamoDB there is no database level: tables belong
        # directly to your account and region
        table = dynamodb.Table(TABLE_NAME)
        try:
            table.load()
            print('Table with name \'{0}\' was found'.format(TABLE_NAME))

        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
            table = dynamodb.create_table(
                TableName=TABLE_NAME,
                KeySchema=[{'AttributeName': 'partitionKey', 'KeyType': 'HASH'},
                           {'AttributeName': 'id', 'KeyType': 'RANGE'}],
                AttributeDefinitions=[{'AttributeName': 'partitionKey', 'AttributeType': 'S'},
                                      {'AttributeName': 'id', 'AttributeType': 'S'}],
                ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5})
            table.wait_until_exists()
            print('Table with name \'{0}\' created'.format(TABLE_NAME))

        create_items(table)
        read_item(table, 'SalesOrder1', 'Account1')
        read_items(table)
        query_items(table, 'Account1')
        replace_item(table, 'SalesOrder1', 'Account1')
        upsert_item(table, 'SalesOrder1', 'Account1')
        delete_item(table, 'SalesOrder1', 'Account1')

        # cleanup the table after sample
        # table.delete()

    except ClientError as e:
        print('\nrun_sample has caught an error. {0}'.format(e.response['Error']['Message']))

    finally:
        print("\nrun_sample done")


if __name__ == '__main__':
    run_sample()
