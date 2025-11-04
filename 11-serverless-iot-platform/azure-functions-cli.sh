#!/bin/bash

FUNCTION_APP_NAME="cdv-iot-platform-functions"

# To install on Linux machines. For Windows download an installer file
# sudo apt-get install azure-functions-core-tools-4

cd iot-function-app

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

func init --python

# To create functions from scratch based on the HTTP trigger template
# func new --name device --template "HTTP trigger" --authlevel "function"

# func new --name house --template "HTTP trigger" --authlevel "function"

# func new --name rooms --template "HTTP trigger" --authlevel "function"

# For local testing
func start 

# Deploy the Function App code
func azure functionapp publish $FUNCTION_APP_NAME