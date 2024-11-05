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
2. Install globally via pip: `pip3 install pipenv==2023.8.281`
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
   5. Create network security group rule for the virtual machine scale using the terminal environmental variables to open the 8080 port that will be used later by the HTTP server in a Docker container 
   ```bash
      az network nsg rule create \
         --resource-group $RESOURCE_GROUP \
         --nsg-name ${VM_NAME}NSG \
         --name allow-http \
         --protocol tcp \
         --priority 1020 \
         --destination-port-range 1883 \
         --access allow
   ```
9. Access the Virtual machine using "SSH using Azure CLI" on the Azure portal
10. In the SSH of the Virtual Machine issue the following commands:
   1. Create Dockerfile 
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
   5. Add Docker to sudo group
   ```bash
      sudo groupadd docker
      sudo usermod -aG docker $USER
      sudo reboot
   ```
   6. Connect once again via SSH after the VM rebooted
   7. Run the the following command to start the MQTT broker
   ```bash
      docker-compose up
   ```
11. Test Python MQTT client `simple_mqtt_device_simulator.py`
12. Follow commands from `azure-cli-create-iot-hub.sh` in the Azure Cloud Shell
13. Test Python MQTT client `simple_mqtt_device_simulator.py`
14. Delete resource group