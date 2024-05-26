## Azure IoT Hub - Bicep

Task: Deploy an Azure IoT Hub using Bicep

## Tested environments
Ubuntu 22.04
Python 3.10.12

### Prerequisites
```
pip3 install pipenv==2023.8.28
```

### Project packages installation
```bash
pipenv install
```

## Run simple MQTT client
```bash
pipenv run python simple_azure_device_simulator.py
```

Deploy the Bicep file using Azure CLI
```
az group create --name cloud-computing --location eastus
az deployment group create --resource-group cloud-computing --template-file main.bicep --parameters appInsightsLocation=<app-location>
```
