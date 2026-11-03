import base64
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info('Python HTTP trigger function processed a request.')

    # Query string parameter, for example ?name=Student
    name = (event.get('queryStringParameters') or {}).get('name')
    if not name and event.get('body'):
        body = event['body']
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        try:
            name = json.loads(body).get('name')
        except (ValueError, AttributeError):
            pass

    if name:
        message = f"Hello, {name}. This HTTP-triggered function executed successfully."
    else:
        message = ("This HTTP-triggered function executed successfully. Pass a name in the query string "
                   "or in the request body for a personalized response.")
    return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": message}
