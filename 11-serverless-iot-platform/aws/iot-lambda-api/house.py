import logging

from botocore.exceptions import ClientError

from common import dynamodb, http_method, is_authorized, json_body, query_param, response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

table = dynamodb.Table('house-data')


def lambda_handler(event, context):
    if not is_authorized(event):
        return response(401, {'error': 'Missing or wrong code (API key)'})

    # Check if the request is a GET request
    if http_method(event) == 'GET':
        house_id = query_param(event, 'house_id')
        if not house_id:
            return response(400, 'Please pass a house_id in the query string')
        try:
            # Read one item by its key
            item = table.get_item(Key={'id': house_id}).get('Item')
            if not item:
                return response(404, 'No data found for the given house id')
            # A list, like the result of the Cosmos DB query in the Azure version
            return response(200, [item])
        except ClientError as e:
            logger.error(f'DynamoDB error: {e}')
            return response(500, 'Error querying DynamoDB')

    # Check if the request is a POST request
    if http_method(event) == 'POST':
        try:
            req_body = json_body(event)
            logger.info(req_body)

            # Create the house entity
            house_data = {
                'id': req_body.get('id'),
                'houseid': req_body.get('name'),
                'location': req_body.get('location'),
            }
            if not house_data['id']:
                return response(400, {'error': 'Invalid request body: id is required'})

            # Create the house entity in the table, only if no house with this id exists yet
            table.put_item(Item=house_data, ConditionExpression='attribute_not_exists(id)')

            return response(201, {'message': 'House entity created successfully'})
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return response(409, {'error': 'A house with this id already exists'})
            logger.error(f'Error creating house entity: {e}')
            return response(500, {'error': 'Failed to create house entity'})
        except (ValueError, AttributeError) as e:
            logger.error(f'Invalid request body: {e}')
            return response(400, {'error': 'Invalid request body'})

    return response(400, 'Invalid request method')
