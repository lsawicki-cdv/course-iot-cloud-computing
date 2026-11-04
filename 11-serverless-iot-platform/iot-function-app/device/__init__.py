import logging
import os
from azure.cosmos import CosmosClient, exceptions

import azure.functions as func
import json

# Initialize the Cosmos client with the endpoint and the key from the app settings
# (COSMOS_ENDPOINT and COSMOS_KEY), so the key is not in the code. In production: Azure Key Vault
endpoint = os.environ["COSMOS_ENDPOINT"]
key = os.environ["COSMOS_KEY"]
client = CosmosClient(endpoint, key)

# Define the database and container
database_name = "iot-platform-database"
container_name = "iot-data"
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)


def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check if the request is a GET request
    if req.method != "GET":
        return func.HttpResponse(
            "Please make a GET request",
            status_code=400
        )

    device_id = req.params.get('device_id')

    try:
        # Query the container
        # The value is passed as a parameter, never pasted into the query text (no SQL injection)
        query = 'SELECT * FROM c WHERE c.deviceid = @device_id'
        logging.info(f'{query} (device_id={device_id})')
        items = list(container.query_items(
            query=query,
            parameters=[{"name": "@device_id", "value": device_id}],
            enable_cross_partition_query=True
        ))

        # Convert items to JSON
        items_json = [dict(item) for item in items]

        if not items_json:
            return func.HttpResponse(
                "No data found for the given device_id",
                status_code=404
            )

        # Filter out the system properties
        for item in items_json:
            item.pop("_rid", None)
            item.pop("_self", None)
            item.pop("_etag", None)
            item.pop("_attachments", None)
            item.pop("_ts", None)

        # Encode the JSON in UTF-8
        items_json = json.dumps(items_json, indent=True, ensure_ascii=False)

        return func.HttpResponse(
            body=items_json,
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",  # Add CORS header
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",  # Allow methods
                "Access-Control-Allow-Headers": "Content-Type"  # Allow headers
            },
            mimetype="application/json"
        )
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"Cosmos DB error: {e}")
        return func.HttpResponse(
            "Error querying Cosmos DB",
            status_code=500
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return func.HttpResponse(
            "Unexpected error occurred",
            status_code=500
        )
