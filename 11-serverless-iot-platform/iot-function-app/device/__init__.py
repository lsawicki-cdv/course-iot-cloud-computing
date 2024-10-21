import logging
from azure.cosmos import CosmosClient, exceptions

import azure.functions as func

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

        if not items_json:
            return func.HttpResponse(
                "No data found for the given device_id",
                status_code=404
            )

        return func.HttpResponse(
            body=str(items_json),
            status_code=200,
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
