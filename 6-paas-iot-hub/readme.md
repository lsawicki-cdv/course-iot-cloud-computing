## Azure IoT Hub - MQTT Device Simulator Exercise

In this exercise, you will learn how to send data from IoT devices to the cloud using MQTT protocol. You'll progress through three stages:
1. **Testing locally** with a public MQTT test server
2. **Running your own MQTT broker** on an Azure Virtual Machine
3. **Connecting to Azure IoT Hub** - Azure's managed IoT service

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## Tested Environments
- Ubuntu 22.04
- Python 3.10.12

## Part 1: Setup and Test with Public MQTT Server
### Step 1: Install Prerequisites
Make sure you have installed:
- Python 3.10 or higher
- pip (Python package manager)
- VS Code

### Step 2: Setup Your Development Environment

1. Clone this repository to your computer
2. Open VS Code and navigate to this directory: `6-paas-iot-hub`
3. Open the integrated terminal in VS Code

### Step 3: Create Python Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows:**
```powershell
py -m venv .venv
.venv\scripts\activate
```

### Step 4: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Configure Your Device ID

Open `simple_mqtt_device_simulator.py` and change the `device_id` to something unique (this helps identify your device's messages):

```python
device_id = "student_yourname_device01"  # Make this unique - don't copy this exact value!
```

**Important:** Choose a unique name - if multiple students use the same ID, you'll see each other's messages!

### Step 6: Test with Public MQTT Server

Run your device simulator (it will connect to the public Mosquitto test server by default):
```bash
python simple_mqtt_device_simulator.py
```

You should see connection logs in the terminal. Look for the MQTT topic name in the output.

### Step 7: Verify Your Messages

1. Open [MQTT Test Client](https://testclient-cloud.mqtt.cool/) in your web browser
2. Connect to the Mosquitto Test Server: `test.mosquitto.org`
3. Subscribe to the topic shown in your terminal logs (example: `devices/student_yourname_device01/messages`)
4. You should now see the messages from your simulator appearing in the web client!

**Stop your simulator (Ctrl+C) before continuing to the next part.**

---

## Part 2: Run Your Own MQTT Broker on Azure VM

Now you'll create your own MQTT broker instead of using the public test server. This gives you more control and privacy.

### Step 8: Create Azure Virtual Machine

Open **Azure Cloud Shell** from the Azure Portal.

**Option A: Using Bash (recommended)**

**Set the environment variables one by one:**

Set the resource group name:
```bash
RESOURCE_GROUP="myResourceGroupVMForDocker"
```

Set the Azure region (change if needed):
```bash
LOCATION="uksouth"
```

Set the VM name:
```bash
VM_NAME="my-vm-mqtt-docker"
```

Set the VM image:
```bash
IMAGE="Ubuntu2204"
```

Set the VM size:
```bash
SIZE="Standard_B1s"
```

**Create the resource group:**
```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Create the virtual machine (this will take a few minutes):**
```bash
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image $IMAGE \
  --size $SIZE \
  --admin-username azureuser \
  --generate-ssh-keys
```

**Important:** The command output will show your VM's **public IP address**. Copy and save it - you'll need it later!

**Install Docker on the VM:**
```bash
az vm extension set \
  --resource-group $RESOURCE_GROUP \
  --vm-name $VM_NAME \
  --name DockerExtension \
  --publisher Microsoft.Azure.Extensions \
  --version 1.0 \
  --settings '{"docker": {"port": "2375"}}'
```

**Open port 1883 for MQTT traffic:**
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

**Option B: Using PowerShell**

**Set the environment variables one by one:**

Set the resource group name:
```powershell
$RESOURCE_GROUP="myResourceGroupVMForDocker"
```

Set the Azure region (change if needed):
```powershell
$LOCATION="uksouth"
```

Set the VM name:
```powershell
$VM_NAME="my-vm-mqtt-docker"
```

Set the VM image:
```powershell
$IMAGE="Ubuntu2204"
```

Set the VM size:
```powershell
$SIZE="Standard_B1s"
```

**Create the resource group:**
```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Create the virtual machine (this will take a few minutes):**
```powershell
az vm create `
  --resource-group $RESOURCE_GROUP `
  --name $VM_NAME `
  --image $IMAGE `
  --size $SIZE `
  --admin-username azureuser `
  --generate-ssh-keys
```

**Important:** The command output will show your VM's **public IP address**. Copy and save it - you'll need it later!

**Install Docker on the VM:**
```powershell
az vm extension set `
  --resource-group $RESOURCE_GROUP `
  --vm-name $VM_NAME `
  --name DockerExtension `
  --publisher Microsoft.Azure.Extensions `
  --version 1.0 `
  --settings '{\"docker\": {\"port\": \"2375\"}}'
```

**Open port 1883 for MQTT traffic:**
```powershell
az network nsg rule create `
  --resource-group $RESOURCE_GROUP `
  --nsg-name ${VM_NAME}NSG `
  --name allow-mqtt `
  --protocol tcp `
  --priority 1020 `
  --destination-port-range 1883 `
  --access allow
```

### Step 9: Configure MQTT Broker on the VM

**Access your VM via SSH:**
1. In the Azure Portal, navigate to your Virtual Machine
2. Click **"Connect"** → **"SSH using Azure CLI"**
3. This will open a terminal connected to your VM

**Now run these commands inside the VM:**

Create a Docker Compose file:
```bash
nano docker-compose.yml
```

Copy and paste this content, then save (press `Ctrl+X`, then `Y`, then `Enter`):
```yaml
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

Create Mosquitto configuration file:
```bash
nano mosquitto.conf
```

Copy and paste this content, then save (`Ctrl+X`, `Y`, `Enter`):
```
allow_anonymous true
listener 1883
```

Set up Docker permissions and reboot:
```bash
sudo groupadd docker
sudo usermod -aG docker $USER
sudo reboot
```

**Wait about 30 seconds for the VM to reboot**, then reconnect via SSH (repeat Step 9 access instructions).

Start the MQTT broker:
```bash
docker compose up
```

You should see logs showing Mosquitto is running. **Leave this terminal open** - the broker needs to keep running.

### Step 10: Connect Your Simulator to Your MQTT Broker

Go back to VS Code and edit `simple_mqtt_device_simulator.py`.

Update the MQTT broker hostname with your VM's public IP address:
```python
mqtt_hub_hostname = "20.123.45.67"  # Replace with YOUR VM's public IP!
mqtt_hub_port = 1883
```

Run your simulator:
```bash
python simple_mqtt_device_simulator.py
```

Your device is now sending messages to your own MQTT broker! Check the Docker logs in the VM terminal to see the connections.

**Stop your simulator (`Ctrl+C`) before continuing.**

---

## Part 3: Connect to Azure IoT Hub

Now you'll connect to Azure IoT Hub - a managed service with enterprise features like device management, security, and Azure service integration.

### Step 11: Create Azure IoT Hub

Go back to **Azure Cloud Shell**.

**Option A: Using Bash (recommended)**

**Set the environment variables one by one:**

Set the resource group name:
```bash
RESOURCE_GROUP="myIotHubResourceGroup"
```

Set the Azure region:
```bash
LOCATION="uksouth"
```

Set the IoT Hub name (**must be globally unique** - change this!):
```bash
IOT_HUB_NAME="iot-hub-yourname-12345"
```

Set your device name:
```bash
IOT_DEVICE_NAME="my-device-01"
```

**Create the resource group:**
```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Create the IoT Hub (this will take a few minutes):**
```bash
az iot hub create \
  --resource-group $RESOURCE_GROUP \
  --name $IOT_HUB_NAME \
  --location $LOCATION \
  --sku F1 \
  --partition-count 2
```

**Register your device with IoT Hub:**
```bash
az iot hub device-identity create \
  --hub-name $IOT_HUB_NAME \
  --device-id $IOT_DEVICE_NAME
```

**Generate authentication token (SAS token):**
```bash
az iot hub generate-sas-token \
  --hub-name $IOT_HUB_NAME \
  --device-id $IOT_DEVICE_NAME \
  --output table
```

**Important:** Copy the **SAS token** from the output - you'll need it in the next step!

**Option B: Using PowerShell**

**Set the environment variables one by one:**

Set the resource group name:
```powershell
$RESOURCE_GROUP="myIotHubResourceGroup"
```

Set the Azure region:
```powershell
$LOCATION="uksouth"
```

Set the IoT Hub name (**must be globally unique** - change this!):
```powershell
$IOT_HUB_NAME="iot-hub-yourname-12345"
```

Set your device name:
```powershell
$IOT_DEVICE_NAME="my-device-01"
```

**Create the resource group:**
```powershell
az group create --name $RESOURCE_GROUP --location $LOCATION
```

**Create the IoT Hub (this will take a few minutes):**
```powershell
az iot hub create `
  --resource-group $RESOURCE_GROUP `
  --name $IOT_HUB_NAME `
  --location $LOCATION `
  --sku F1 `
  --partition-count 2
```

**Register your device with IoT Hub:**
```powershell
az iot hub device-identity create `
  --hub-name $IOT_HUB_NAME `
  --device-id $IOT_DEVICE_NAME
```

**Generate authentication token (SAS token):**
```powershell
az iot hub generate-sas-token `
  --hub-name $IOT_HUB_NAME `
  --device-id $IOT_DEVICE_NAME `
  --output table
```

**Important:** Copy the **SAS token** from the output - you'll need it in the next step!

### Step 12: Configure Simulator for Azure IoT Hub

Go back to VS Code and open `simple_mqtt_device_simulator.py`.

Update these three values with the information from your IoT Hub:

Set your device ID:
```python
device_id = "my-device-01"  # Use the device ID you created
```

Set your SAS token (paste the full token):
```python
sas_token = "SharedAccessSignature sr=iot-hub..."  # Paste your SAS token here
```

Set your IoT Hub name:
```python
iot_hub_name = "iot-hub-yourname-12345"  # Use your IoT Hub name
```

**Uncomment the authentication and security lines** (remove the `#` at the start):

```python
print(iot_hub_name+".azure-devices.net/" +
      device_id + "/?api-version=2021-04-12")
client.username_pw_set(username=iot_hub_name+".azure-devices.net/" +
                       device_id + "/?api-version=2021-04-12", password=sas_token)

client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None,
               cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
client.tls_insecure_set(False)
```

Update the connection settings to use Azure IoT Hub hostname and secure port:

```python
mqtt_hub_hostname = "iot-hub-yourname-12345.azure-devices.net"  # Your IoT Hub hostname
mqtt_hub_port = 8883  # Secure MQTT port (MQTTS)
```

### Step 13: Monitor Messages in Azure IoT Hub

Install the Azure IoT Hub extension in VS Code:
1. Click the Extensions icon in VS Code
2. Search for "Azure IoT Hub"
3. Install the extension
4. Sign in to your Azure account

Start monitoring your IoT Hub:
1. In the Azure IoT Hub extension panel, find your IoT Hub
2. Right-click your IoT Hub
3. Select **"Start Monitoring Built-in Event Endpoint"**

### Step 14: Run Your Simulator

Run your simulator:
```bash
python simple_mqtt_device_simulator.py
```

You should now see your messages appearing in the VS Code output panel! Your device is successfully connected to Azure IoT Hub.

---

## Cleanup

**Don't forget to delete your resources to avoid charges!**

Delete the VM resource group:
```bash
az group delete --name myResourceGroupVMForDocker --yes --no-wait
```

Delete the IoT Hub resource group:
```bash
az group delete --name myIotHubResourceGroup --yes --no-wait
```
