import logging
from azure.cosmos import CosmosClient, exceptions

import azure.functions as func
import json

# Initialize the Cosmos client
endpoint = "https://cosmos-db-account-iot-platform.documents.azure.com:443/"
# Replace with your Cosmos DB key, place in Azure Key Vault in production
key = "<master_key>"
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
        query = f'SELECT * FROM c WHERE c.deviceid = "{device_id}"'
        logging.info(query)
        items = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        # Convert items to JSON
        items_json = [dict(item) for item in items]

        # Filter out the system properties
        for item in items_json:
            item.pop("_rid", None)
            item.pop("_self", None)
            item.pop("_etag", None)
            item.pop("_attachments", None)
            item.pop("_ts", None)

        # Encode the JSON in UTF-8
        items_json = json.dumps(items_json, indent=True, ensure_ascii=False)

        if not items_json:
            return func.HttpResponse(
                "No data found for the given device_id",
                status_code=404
            )

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
