## Azure Iot Hub

## Tested environments
Ubuntu 22.04
Python 3.10.12

## Exercise
1. Be sure that you have installed Python, Pip and VS Code
2. Clone the repository to your computer
3. Go to this directory in the terminal in VS Code (`6-paas-iot-hub`)
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
7. Change the Python MQTT client `simple_mqtt_device_simulator.py`. Change the `device_id` value to something unique
    ```Python
      device_id = "some_unique_name_to_figure_out_on_your_own_dont_copy"
    ```
8. Run Python device simulator `python simple_mqtt_device_simulator.py`. It will connect by default to the [Mosquitto Test Server](https://test.mosquitto.org/)
9. Go to [MQTT test client](https://testclient-cloud.mqtt.cool/), connect the [Mosquitto Test Server](https://test.mosquitto.org/) and subscribe (so you can receive messages) to the MQTT topic mentioned in the `simple_mqtt_device_simulator.py` (it should be visible in logs in the terminal)
10. Issue the following commands in **the Azure Cloud Shell (Bash)**
    1.  Set the terminal environmental variables
    ```bash
      RESOURCE_GROUP="myResourceGroupVMForDocker"
    ```
    ```bash
      LOCATION="uksouth"
    ```
    ```bash
      VM_NAME="my-vm-mqtt-docker"
    ```
    ```bash
      IMAGE="Ubuntu2204"
    ```
    ```bash
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
11. Access the Virtual machine using "SSH using Azure CLI" on the Azure portal
12. In the SSH of the Virtual Machine issue the following commands:
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
    3. Create a mosquitto configuration file
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
      docker compose up
    ```
13. Change the MQTT device simulator `simple_mqtt_device_simulator.py` so it connects to the MQTT broker on the Virtual Machine (paste the public IP address)
14. Issue the following commands in **the Azure Cloud Shell (Bash)** to create Azure IoT Hub
    1.  Set the terminal environmental variables
    ```bash
    RESOURCE_GROUP="myIotHubResourceGroup"
    ```
    ```bash
    LOCATION="uksouth"
    ```
    ```bash
    IOT_HUB_NAME="my-super-iot-hub"
    ```
    ```bash
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
15. Change the Python MQTT client `simple_mqtt_device_simulator.py` to connect to Azure IoT Hub. Update the following lines
    ```Python
      device_id = "<device-id>"
      sas_token = "<device-sas-token>"
      iot_hub_name = "<iot-hub-name>"
    ```
16. Uncomment the following lines
    ```Python
    print(iot_hub_name+".azure-devices.net/" +
          device_id + "/?api-version=2021-04-12")
    client.username_pw_set(username=iot_hub_name+".azure-devices.net/" +
                           device_id + "/?api-version=2021-04-12", password=sas_token)

    client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None,
                   cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
    client.tls_insecure_set(False)
    ```
17. Change the hub URL and port to `8883` (a standard one for MQTTS communication)
    ```Python
    client.connect("<URL>", port=8883)
    ```
18. Install the Azure IoT Hub extensions in VS Code
19. Start monitoring endpoint from your Azure IoT Hub using the mentioned extension in VS Code
20. Delete resource group