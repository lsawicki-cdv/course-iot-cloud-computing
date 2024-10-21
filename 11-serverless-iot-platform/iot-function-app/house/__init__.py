import logging

from azure.cosmos import CosmosClient, exceptions
from azure.functions import HttpRequest, HttpResponse
import json

# Initialize the Cosmos client
endpoint = "https://cosmos-db-account-iot-platform.documents.azure.com:443/"
# Replace with your Cosmos DB key, place in Azure Key Vault in production
key = "<master_key>"
client = CosmosClient(endpoint, key)

# Define the database and container
database_name = "iot-platform-database"
container_name = "house-data"
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)


def main(req: HttpRequest) -> HttpResponse:
    # Check if the request is a GET request
    if req.method == "GET":
        try:
            house_id = req.params.get('house_id')

            # Query the container
            query = f'SELECT * FROM c WHERE c.id = "{house_id}"'
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
            items_json = json.dumps(
                items_json, indent=True, ensure_ascii=False)

            return HttpResponse(
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
            return HttpResponse(
                "Error querying Cosmos DB",
                status_code=500
            )
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return HttpResponse(
                "Error querying Cosmos DB",
                status_code=500
            )

    # Check if the request is a POST request
    if req.method != 'POST':
        return HttpResponse(
            'Please make a POST request',
            status_code=400,
            mimetype='application/json'
        )

    try:
        # Parse the request body
        req_body = req.get_json()

        print(req_body)

        # Create the house entity
        house_data = {
            'id': req_body.get('id'),
            'houseid': req_body.get('name'),
            'location': req_body.get('location'),
        }

        # Create the house entity in the Cosmos DB container
        container.create_item(body=house_data)

        return HttpResponse(
            json.dumps({'message': 'House entity created successfully'}),
            status_code=201,
            headers={
                "Access-Control-Allow-Origin": "*",  # Add CORS header
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",  # Allow methods
                "Access-Control-Allow-Headers": "Content-Type"  # Allow headers
            },
            mimetype='application/json'
        )
    except exceptions.CosmosHttpResponseError as e:
        logging.error(f'Error creating house entity: {e}')
        return HttpResponse(
            json.dumps({'error': 'Failed to create house entity'}),
            status_code=500,
            mimetype='application/json'
        )
    except ValueError as e:
        logging.error(f'Invalid request body: {e}')
        return HttpResponse(
            json.dumps({'error': 'Invalid request body'}),
            status_code=400,
            mimetype='application/json'
        )
