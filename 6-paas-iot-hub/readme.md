## Azure Iot Hub

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
pipenv run python simple_mqtt_device_simulator.py
```

## Exercise
1. Be sure that you have installed Python, Pip and VS Code
2. Install globally via pip: `pip3 install pipenv==2023.8.28`
3. Clone the repository to your computer
4. Go to this directory in the terminal in VS Code (`6-paas-iot-hub`)
5. Install Python dependencies: `pipenv install`
6. Change to the `simple_mqtt_device_simulator.py` application to connect the [Mosquitto Test Server](https://test.mosquitto.org/)
7. Go to [MQTT test client](https://testclient-cloud.mqtt.cool/), connect the [Mosquitto Test Server](https://test.mosquitto.org/) and subscribe to the topic mentioned in the `simple_mqtt_device_simulator.py`
8. Issue the following commands in **the Azure Cloud Shell**
   1. Set the terminal environmental variables 
   ```bash
      RESOURCE_GROUP="myResourceGroupVMForDocker"
      LOCATION="uksouth"
      VM_NAME="my-vm-mqtt-docker"
      IMAGE="Ubuntu2204"
      SIZE="Standard_B1s"
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a virtual machine using the terminal environmental variables
   ```bash
      az vm create \
         --resource-group $RESOURCE_GROUP \
         --name $VM_NAME \
         --image $IMAGE \
         --size $SIZE \
         --admin-username azureuser \
         --generate-ssh-keys
   ```
   4. Install the docker engine on the virtual machine set using the terminal environmental variables
   ```bash
      az vm extension set \
         --resource-group $RESOURCE_GROUP \
         --vm-name $VM_NAME \
         --name DockerExtension \
         --publisher Microsoft.Azure.Extensions \
         --version 1.0 \
         --settings '{"docker": {"port": "2375"}}'
   ```
   5. Create network security group rule for the virtual machine scale using the terminal environmental variables to open the 1883 port that will be used later by the MQTT broker in a Docker container 
   ```bash
      az network nsg rule create \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${VM_NAME}NSG \
         --name allow-mqtt \
         --protocol tcp \
         --priority 1020 \
         --destination-port-range 1883 \
         --access allow
   ```
9. Access the Virtual machine using "SSH using Azure CLI" on the Azure portal
10. In the SSH of the Virtual Machine issue the following commands:
    1.  Create Docker compose file 
    ```bash
      nano docker-compose.yml
    ```
    2. Copy the following content to the terminal and save it on the virtual machine
    ```
    version: "3.8"

    services:
    mqtt-broker:
    image: eclipse-mosquitto:latest
    container_name: mqtt-broker
    ports:
        - "1883:1883"
    volumes:
    - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    ```
    3. Create HTML file
    ```bash
      nano mosquitto.conf
    ```
    4. Copy the following content to the terminal and save it on the virtual machine
    ```
        allow_anonymous true
        listener 1883
    ```
    5. Run the the following command to start the MQTT broker
    ```bash
      docker compose up
    ```
11. Test Python MQTT client `simple_mqtt_device_simulator.py` with the MQTT broker on the Virtual Machine
12. Issue the following commands in **the Azure Cloud Shell** to create Azure IoT Hub
   1. Set the terminal environmental variables 
   ```bash
    RESOURCE_GROUP="myIotHubResourceGroup"
    LOCATION="uksouth"
    IOT_HUB_NAME="my-super-iot-hub"
    IOT_DEVICE_NAME="my-new-device"
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create the Azure IoT Hub using the terminal environmental variables
   ```bash
      az iot hub create --resource-group $RESOURCE_GROUP --name $IOT_HUB_NAME --location $LOCATION --sku F1 --partition-count 2
   ```
   4. Create the device identity on Azure IoT Hub
   ```bash
      az iot hub device-identity create --hub-name $IOT_HUB_NAME --device-id $IOT_DEVICE_NAME
   ```
   5. Get SAS token for the IoT Hub
   ```bash
      az iot hub generate-sas-token --hub-name $IOT_HUB_NAME --device-id $IOT_DEVICE_NAME --output table
   ```
13. Change the Python MQTT client `simple_mqtt_device_simulator.py` to connect to Azure IoT Hub
14. Install the Azure IoT Hub extensions in VS Code
15. Start monitoring endpoint from your Azure IoT Hub using the mentioned extension in VS Code
16. Delete resource group