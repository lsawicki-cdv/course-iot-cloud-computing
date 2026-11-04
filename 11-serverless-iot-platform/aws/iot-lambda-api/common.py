import base64
import hmac
import json
import os
from decimal import Decimal

import boto3

# One DynamoDB connection, reused by every request the function handles
dynamodb = boto3.resource('dynamodb')

# The API key, like the function key of Azure Functions. Requests must add ?code=<key> to the URL.
# Keep it in an environment variable, not in the code (in production: AWS Secrets Manager)
API_KEY = os.environ.get('API_KEY', '')


def is_authorized(event):
    code = (event.get('queryStringParameters') or {}).get('code', '')
    # compare_digest takes the same time for every wrong key, so the key can't be guessed letter by letter
    return bool(API_KEY) and hmac.compare_digest(code, API_KEY)


def query_param(event, name):
    return (event.get('queryStringParameters') or {}).get(name)


def http_method(event):
    return event['requestContext']['http']['method']


def json_body(event):
    # Raises ValueError if the body isn't valid JSON
    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        body = base64.b64decode(body).decode('utf-8')
    return json.loads(body, parse_float=Decimal)


def to_json(value):
    # DynamoDB returns numbers as Decimal, which json.dumps can't write
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def response(status_code, body):
    # CORS headers are added by the API Gateway CORS configuration
    if not isinstance(body, str):
        body = json.dumps(body, indent=True, ensure_ascii=False, default=to_json)
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': body,
    }
