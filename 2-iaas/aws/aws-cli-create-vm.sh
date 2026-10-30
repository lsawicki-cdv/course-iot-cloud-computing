#!/bin/bash

# Variables
REGION="eu-west-2"
VM_NAME="my-vm"
SECURITY_GROUP_NAME="my-vm-sg"
IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
SIZE="t3.micro"

# Download the nginx installation script (passed to the VM as user data)
curl -o vm.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh

# Create a security group in the default VPC
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name $SECURITY_GROUP_NAME \
  --description "Security group for $VM_NAME" \
  --query GroupId \
  --output text)

# Allow SSH (port 22)
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

# Create a virtual machine and install nginx server using user data
INSTANCE_ID=$(aws ec2 run-instances \
  --region $REGION \
  --image-id $IMAGE \
  --instance-type $SIZE \
  --security-group-ids $SECURITY_GROUP_ID \
  --associate-public-ip-address \
  --user-data file://vm.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_NAME}]" \
  --query "Instances[0].InstanceId" \
  --output text)

aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID

# List security group rules
aws ec2 describe-security-group-rules \
  --region $REGION \
  --filters Name=group-id,Values=$SECURITY_GROUP_ID \
  --output table

# Create security group rule to open the http port (80)
aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Get public IP address
IP_ADDRESS=$(aws ec2 describe-instances \
  --region $REGION \
  --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

curl --connect-timeout 5 http://$IP_ADDRESS

# Delete the virtual machine and the security group
# aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID
# aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID
# aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
