## AWS IoT Core - MQTT Device Simulator Exercise

This is the AWS version of the [Azure IoT Hub exercise](../readme.md). You will learn how to send data from IoT devices to the cloud using MQTT protocol, in three stages:
1. **Testing locally** with a public MQTT test server
2. **Running your own MQTT broker** on an AWS EC2 virtual machine
3. **Connecting to AWS IoT Core** - AWS's managed IoT service

| Azure | AWS |
|-------|-----|
| Virtual Machine with the Docker extension | EC2 instance with Docker installed by user data |
| Azure IoT Hub | AWS IoT Core (there is one per account and region - you don't create it) |
| IoT Hub name (`<name>.azure-devices.net`) | Account's IoT endpoint (`<id>-ats.iot.<region>.amazonaws.com`) |
| Device identity | Thing |
| SAS token (username and password) | X.509 device certificate and private key (no username or password) |
| Access defined by the token | IoT policy attached to the certificate |
| `root_cert.pem` (DigiCert Global Root G2) | `AmazonRootCA1.pem` (Amazon Root CA 1) |
| VS Code "Start Monitoring Built-in Event Endpoint" | MQTT test client in the AWS Console |
| Resource group | No direct equivalent - resources are deleted one by one |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. The EC2 instance (t3.micro) and AWS IoT Core are Free Tier eligible (IoT Core: 500,000 messages per month; the simulator sends one message every 10 seconds). Delete all resources at the end of the exercise.

## Tested Environments
- Ubuntu 26.04
- Python 3.10+

## Part 1: Setup and Test with Public MQTT Server
### Step 1: Install Prerequisites
Make sure you have installed:
- Python 3.10 or higher
- pip (Python package manager)
- VS Code

### Step 2: Setup Your Development Environment

1. Clone this repository to your computer
2. Open VS Code and navigate to this directory: `6-paas-iot-mqtt/aws`
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
pip install -r ../requirements.txt
```

### Step 5: Configure Your Device ID

Open `simple_mqtt_device_simulator.py` (the AWS version, in the `aws` folder) and change the `device_id` to something unique (this helps identify your device's messages):

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

If the simulator can't connect (`Network is unreachable` or a timeout), the public test server may be down. Use another public test server instead: set `mqtt_hub_hostname = "broker.hivemq.com"` in the simulator, and connect the web client in the next step to `broker.hivemq.com`.

### Step 7: Verify Your Messages

1. Open [MQTT Test Client](https://testclient-cloud.mqtt.cool/) in your web browser
2. Connect to the Mosquitto Test Server: `test.mosquitto.org`
3. Subscribe to the topic shown in your terminal logs (example: `devices/student_yourname_device01/messages/events/`)
4. You should now see the messages from your simulator appearing in the web client!

**Stop your simulator (Ctrl+C) before continuing to the next part.**

---

## Part 2: Run Your Own MQTT Broker on an AWS EC2 Virtual Machine

Now you'll create your own MQTT broker instead of using the public test server. This gives you more control and privacy.

### Step 8: Create the EC2 Virtual Machine

Open **AWS CloudShell** (the terminal icon in the AWS Console's top bar).

**Option A: Using Bash (recommended)**

**Set the environment variables one by one:**

Set the AWS region (change if needed):
```bash
REGION="eu-west-2"
```

Set the VM name:
```bash
VM_NAME="my-vm-mqtt-docker"
```

Set the VM image (Ubuntu 26.04):
```bash
IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
```

Set the VM size:
```bash
SIZE="t3.micro"
```

**Download the script that installs Docker on the VM (it is passed to the VM as user data, a script run on its first boot):**
```bash
curl -o install-docker.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/6-paas-iot-mqtt/aws/install-docker.sh
```

**Create a security group:**
```bash
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name ${VM_NAME}-sg \
  --description "Security group for $VM_NAME" \
  --query GroupId \
  --output text)
```

**Open port 22 for SSH and port 1883 for MQTT traffic:**
```bash
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0
```
```bash
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 1883 \
  --cidr 0.0.0.0/0
```

**Create the virtual machine, which installs Docker from the user data:**
```bash
INSTANCE_ID=$(aws ec2 run-instances \
  --region $REGION \
  --image-id $IMAGE \
  --instance-type $SIZE \
  --security-group-ids $SECURITY_GROUP_ID \
  --associate-public-ip-address \
  --user-data file://install-docker.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_NAME}]" \
  --query "Instances[0].InstanceId" \
  --output text)
```

**Wait until it is running and show its public IP address:**
```bash
aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
```
```bash
aws ec2 describe-instances \
  --region $REGION \
  --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text
```

**Important:** Copy and save the **public IP address** - you'll need it later!

**Option B: Using PowerShell**

Start PowerShell in AWS CloudShell by typing `pwsh`.

**Set the environment variables one by one:**

Set the AWS region (change if needed):
```powershell
$REGION="eu-west-2"
```

Set the VM name:
```powershell
$VM_NAME="my-vm-mqtt-docker"
```

Set the VM image (Ubuntu 26.04):
```powershell
$IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
```

Set the VM size:
```powershell
$SIZE="t3.micro"
```

**Download the script that installs Docker on the VM (it is passed to the VM as user data, a script run on its first boot):**
```powershell
curl -o install-docker.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/6-paas-iot-mqtt/aws/install-docker.sh
```

**Create a security group:**
```powershell
$SECURITY_GROUP_ID=$(aws ec2 create-security-group `
  --region $REGION `
  --group-name "$VM_NAME-sg" `
  --description "Security group for $VM_NAME" `
  --query GroupId `
  --output text)
```

**Open port 22 for SSH and port 1883 for MQTT traffic:**
```powershell
aws ec2 authorize-security-group-ingress `
  --region $REGION `
  --group-id $SECURITY_GROUP_ID `
  --protocol tcp `
  --port 22 `
  --cidr 0.0.0.0/0
```
```powershell
aws ec2 authorize-security-group-ingress `
  --region $REGION `
  --group-id $SECURITY_GROUP_ID `
  --protocol tcp `
  --port 1883 `
  --cidr 0.0.0.0/0
```

**Create the virtual machine, which installs Docker from the user data:**
```powershell
$INSTANCE_ID=$(aws ec2 run-instances `
  --region $REGION `
  --image-id $IMAGE `
  --instance-type $SIZE `
  --security-group-ids $SECURITY_GROUP_ID `
  --associate-public-ip-address `
  --user-data file://install-docker.sh `
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_NAME}]" `
  --query "Instances[0].InstanceId" `
  --output text)
```

**Wait until it is running and show its public IP address:**
```powershell
aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
```
```powershell
aws ec2 describe-instances `
  --region $REGION `
  --instance-ids $INSTANCE_ID `
  --query "Reservations[0].Instances[0].PublicIpAddress" `
  --output text
```

**Important:** Copy and save the **public IP address** - you'll need it later!

### Step 9: Configure MQTT Broker on the VM

**Access your VM via SSH:**
1. In the AWS Console, go to EC2 → Instances and select `my-vm-mqtt-docker`
2. Click **"Connect"** → **"EC2 Instance Connect"** → **"Connect"**
3. This will open a terminal connected to your VM

**Now run these commands inside the VM:**

Wait until the user data script has installed Docker (it prints `status: done`):
```bash
cloud-init status --wait
```

Create a Docker Compose file:
```bash
nano docker-compose.yml
```

Copy and paste this content, then save (press `Ctrl+X`, then `Y`, then `Enter`):
```yaml
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

The user data script has already added the `ubuntu` user to the `docker` group. **Close the EC2 Instance Connect window and connect once again** (repeat Step 9 access instructions), so the group membership takes effect.

Start the MQTT broker:
```bash
docker compose up
```

You should see logs showing Mosquitto is running. **Leave this terminal open** - the broker needs to keep running.

### Step 10: Connect Your Simulator to Your MQTT Broker

Go back to VS Code and edit `simple_mqtt_device_simulator.py` (the AWS version).

Update the MQTT broker hostname with your VM's public IP address:
```python
mqtt_hub_hostname = "18.123.45.67"  # Replace with YOUR VM's public IP!
mqtt_hub_port = 1883
```

Run your simulator:
```bash
python simple_mqtt_device_simulator.py
```

Your device is now sending messages to your own MQTT broker! Check the Docker logs in the VM terminal to see the connections.

**Stop your simulator (`Ctrl+C`) before continuing.**

---

## Part 3: Connect to AWS IoT Core

Now you'll connect to AWS IoT Core - a managed service with device management, security, and integration with other AWS services.

Unlike Azure IoT Hub, you don't create an IoT Core instance: every AWS account has one per region, with its own endpoint (hostname). You register your device as a **thing**, and the device proves its identity with an **X.509 certificate** instead of a SAS token. An **IoT policy** attached to the certificate says what the device may do.

### Step 11: Register Your Device in AWS IoT Core

Go back to **AWS CloudShell**.

**Option A: Using Bash (recommended)**

**Set the environment variables one by one:**

Set the AWS region:
```bash
REGION="eu-west-2"
```

Set your device name (the thing name, also used as the MQTT client ID):
```bash
THING_NAME="my-device-01"
```

Save your AWS account ID (used in the policy):
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**Register your device (create a thing):**
```bash
aws iot create-thing --region $REGION --thing-name $THING_NAME
```

**Create the device certificate and private key, and save the certificate's ARN:**
```bash
CERTIFICATE_ARN=$(aws iot create-keys-and-certificate \
  --region $REGION \
  --set-as-active \
  --certificate-pem-outfile device.pem.crt \
  --private-key-outfile private.pem.key \
  --query certificateArn \
  --output text)
```

**Create an IoT policy that allows the device to connect with its own client ID and publish to its own topics:**
```bash
cat > device-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:topic/devices/$THING_NAME/*"}
  ]
}
EOF
```
```bash
aws iot create-policy \
  --region $REGION \
  --policy-name ${THING_NAME}-policy \
  --policy-document file://device-policy.json
```

**Attach the policy to the certificate, and the certificate to the thing:**
```bash
aws iot attach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
```
```bash
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```

**Show your IoT Core endpoint (the MQTT broker hostname):**
```bash
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

**Important:** Copy the **endpoint** from the output - you'll need it in the next step!

**Option B: Using PowerShell**

**Set the environment variables one by one:**

Set the AWS region:
```powershell
$REGION="eu-west-2"
```

Set your device name (the thing name, also used as the MQTT client ID):
```powershell
$THING_NAME="my-device-01"
```

Save your AWS account ID (used in the policy):
```powershell
$ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

**Register your device (create a thing):**
```powershell
aws iot create-thing --region $REGION --thing-name $THING_NAME
```

**Create the device certificate and private key, and save the certificate's ARN:**
```powershell
$CERTIFICATE_ARN=$(aws iot create-keys-and-certificate `
  --region $REGION `
  --set-as-active `
  --certificate-pem-outfile device.pem.crt `
  --private-key-outfile private.pem.key `
  --query certificateArn `
  --output text)
```

**Create an IoT policy that allows the device to connect with its own client ID and publish to its own topics:**
```powershell
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:${REGION}:${ACCOUNT_ID}:topic/devices/$THING_NAME/*"}
  ]
}
"@ | Set-Content device-policy.json
```
```powershell
aws iot create-policy `
  --region $REGION `
  --policy-name "$THING_NAME-policy" `
  --policy-document file://device-policy.json
```

**Attach the policy to the certificate, and the certificate to the thing:**
```powershell
aws iot attach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
```
```powershell
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```

**Show your IoT Core endpoint (the MQTT broker hostname):**
```powershell
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

**Important:** Copy the **endpoint** from the output - you'll need it in the next step!

### Step 12: Download the Device Certificate and Private Key

The certificate and the private key are files in your CloudShell home folder. The device needs them to connect.

1. In CloudShell, click **"Actions"** → **"Download file"**
2. Enter `/home/cloudshell-user/device.pem.crt` and click **"Download"**
3. Repeat for `/home/cloudshell-user/private.pem.key`
4. Move both files to the `6-paas-iot-mqtt/aws` folder on your computer, next to `simple_mqtt_device_simulator.py` and `AmazonRootCA1.pem`

**Important:** The private key is the device's password. Don't share it or commit it to git (the `aws/.gitignore` file already excludes it). AWS shows the private key only once - if you lose it, create a new certificate.

### Step 13: Configure Simulator for AWS IoT Core

Go back to VS Code and open `simple_mqtt_device_simulator.py` (the AWS version).

Set your device ID - it **must be the same as the thing name**, because the policy only allows this MQTT client ID:
```python
device_id = "my-device-01"  # Use the thing name you created
```

Check the paths to the certificates (the files are in the same folder as the simulator):
```python
path_to_root_cert = "AmazonRootCA1.pem"
path_to_device_cert = "device.pem.crt"
path_to_private_key = "private.pem.key"
```

**Uncomment the security lines** (remove the `#` at the start). There is no `username_pw_set` line, because the device authenticates with its certificate:

```python
client.tls_set(ca_certs=path_to_root_cert, certfile=path_to_device_cert, keyfile=path_to_private_key,
               cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
client.tls_insecure_set(False)
```

Update the connection settings to use your IoT Core endpoint and secure port:

```python
mqtt_hub_hostname = "abcdefgh123456-ats.iot.eu-west-2.amazonaws.com"  # Your IoT Core endpoint
mqtt_hub_port = 8883  # Secure MQTT port (MQTTS)
```

### Step 14: Monitor Messages in AWS IoT Core

1. In the AWS Console, go to **AWS IoT Core** (check the region in the top-right corner)
2. Open **"MQTT test client"** (under "Test")
3. In **"Subscribe to a topic"**, enter `devices/#` and click **"Subscribe"**

### Step 15: Run Your Simulator

Run your simulator:
```bash
python simple_mqtt_device_simulator.py
```

You should now see your messages appearing in the MQTT test client! Your device is successfully connected to AWS IoT Core.

If the simulator keeps disconnecting right after connecting, check that `device_id` is the same as the thing name, and that the region in the endpoint matches the region in the policy. AWS IoT Core closes connections that the policy doesn't allow.

---

## Cleanup

**Don't forget to delete your resources to avoid charges!** Run these commands in **AWS CloudShell**, in the session where you set the variables.

**Delete the virtual machine and its security group:**
```bash
aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID
```
```bash
aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID
```
```bash
aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
```

**Delete the IoT Core resources** (the same commands work in Bash and PowerShell, except for the first one):

Save the certificate ID (the last part of the certificate's ARN) - Bash:
```bash
CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
```
PowerShell:
```powershell
$CERTIFICATE_ID=$CERTIFICATE_ARN.Split('/')[-1]
```

Detach the certificate from the thing and the policy from the certificate:
```bash
aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
```
```bash
aws iot detach-policy --region $REGION --policy-name "$THING_NAME-policy" --target $CERTIFICATE_ARN
```

Deactivate and delete the certificate:
```bash
aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
```
```bash
aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
```

Delete the thing and the policy:
```bash
aws iot delete-thing --region $REGION --thing-name $THING_NAME
```
```bash
aws iot delete-policy --region $REGION --policy-name "$THING_NAME-policy"
```
