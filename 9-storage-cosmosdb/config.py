import os

settings = {
    'host': os.environ.get('ACCOUNT_HOST', '<URL>'),
    'master_key': os.environ.get('ACCOUNT_KEY', '<key>'),
    'database_id': os.environ.get('COSMOS_DATABASE', 'my-super-database'),
    'container_id': os.environ.get('COSMOS_CONTAINER', 'my-super-container'),
}
