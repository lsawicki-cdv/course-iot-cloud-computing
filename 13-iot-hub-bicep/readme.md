## Azure IoT Hub - Bicep

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

Task: Deploy an Azure IoT Hub using Bicep

## Tested environments
Ubuntu 22.04
Python 3.10.12

## Exercise
1. Be sure that you have installed Python, Pip and VS Code
2. Clone the repository to your computer
3. Go to this directory in the terminal in VS Code (`13-iot-hub-bicep`)
4. On **macOS/Linux** type in the terminal the following commands
   ```bash
      python3 -m venv .venv
      source .venv/bin/activate
   ```
5. On **Windows** type in the terminal the following commands
   ```powershell
      py -m venv .venv
      .venv\scripts\activate
   ```
6. Install dependencies: `pip install -r requirements.txt`
7. Deploy the Bicep file using Azure CLI
    ```bash
    az group create --name cloud-computing-iot-hub --location uksouth  # Change to your allowed region if needed
    az deployment group create --resource-group cloud-computing-iot-hub --template-file main.bicep --parameters appInsightsLocation=uksouth  # Change to your allowed region if needed
    ```
8. Go to the Azure IoT Hub (that was created using the Bicep file) -> Device Management -> Devices
9. Add device with symmetric authentication. Copy the primary connection string to `simple_azure_device_simulator.py`  to variable `conn_str`
10. Run Python device simulator `python simple_azure_device_simulator.py`.
11. Check the Azure Blob Storage to see if the messages from the device simulator arrive there

