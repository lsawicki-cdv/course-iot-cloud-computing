import os

settings = {
    'host': os.environ.get('ACCOUNT_HOST', 'https://my-cosmos-super-db.documents.azure.com:443/'),
    'master_key': os.environ.get('ACCOUNT_KEY', '<key>'),
    'database_id': os.environ.get('COSMOS_DATABASE', 'ToDoList'),
    'container_id': os.environ.get('COSMOS_CONTAINER', 'Items'),
}
