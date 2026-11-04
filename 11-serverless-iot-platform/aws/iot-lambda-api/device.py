import logging

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from common import dynamodb, http_method, is_authorized, query_param, response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# The table the IoT rule writes the device telemetry to
table = dynamodb.Table('iot-data')


def lambda_handler(event, context):
    if not is_authorized(event):
        return response(401, {'error': 'Missing or wrong code (API key)'})

    # Check if the request is a GET request
    if http_method(event) != 'GET':
        return response(400, 'Please make a GET request')

    device_id = query_param(event, 'device_id')
    if not device_id:
        return response(400, 'Please pass a device_id in the query string')

    try:
        # Query the table: all readings of one device (the partition key), sorted by timestamp (the sort key)
        logger.info(f'Querying readings of device {device_id}')
        items = []
        kwargs = {'KeyConditionExpression': Key('deviceid').eq(device_id)}
        while True:
            result = table.query(**kwargs)
            items.extend(result['Items'])
            if 'LastEvaluatedKey' not in result:
                break
            kwargs['ExclusiveStartKey'] = result['LastEvaluatedKey']

        if not items:
            return response(404, 'No data found for the given device_id')

        return response(200, items)
    except ClientError as e:
        logger.error(f'DynamoDB error: {e}')
        return response(500, 'Error querying DynamoDB')
