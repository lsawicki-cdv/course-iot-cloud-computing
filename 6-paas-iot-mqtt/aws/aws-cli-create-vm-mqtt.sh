#!/bin/bash

# Variables
REGION="eu-west-2"
VM_NAME="my-vm-mqtt-docker"
IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
SIZE="t3.micro"

# Download the Docker installation script (passed to the VM as user data)
curl -o install-docker.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/6-paas-iot-mqtt/aws/install-docker.sh

# Create a security group and allow SSH (port 22) and MQTT (port 1883)
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name ${VM_NAME}-sg \
  --description "Security group for $VM_NAME" \
  --query GroupId \
  --output text)

aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 1883 \
  --cidr 0.0.0.0/0

# Create a virtual machine and install Docker engine using user data
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

aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID

# Get public IP address
aws ec2 describe-instances \
  --region $REGION \
  --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text

# !!! Access the VM using EC2 Instance Connect and start the MQTT broker (see readme.md)

# Delete the virtual machine and the security group
# aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID
# aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID
# aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
