#!/bin/bash

FUNCTION_APP_NAME="cdv-iot-platform-functions"

sudo apt-get install azure-functions-core-tools-4

cd 11-serverless-iot-platform/iot-function-app

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

func init --python

func new --name device --template "HTTP trigger" --authlevel "function"

func new --name house --template "HTTP trigger" --authlevel "function"

# For local testing
func start 

# Deploy the Function App code
func azure functionapp publish $FUNCTION_APP_NAME