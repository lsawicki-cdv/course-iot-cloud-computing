#!/bin/bash

# Variables
REGION="eu-west-2"
VM_NAME="my-vm-docker"
IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
SIZE="t3.micro"

# Download the Docker engine and AWS CLI installation script (passed to the VM as user data)
curl -o install-docker-aws-cli.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/4-iaas-containers/aws/install-docker-aws-cli.sh

# Create an IAM role that allows the VM to push Docker images to ECR
cat > ec2-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
EOF

aws iam create-role \
  --role-name ${VM_NAME}-role \
  --assume-role-policy-document file://ec2-trust-policy.json

aws iam attach-role-policy \
  --role-name ${VM_NAME}-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam create-instance-profile --instance-profile-name ${VM_NAME}-profile

aws iam add-role-to-instance-profile \
  --instance-profile-name ${VM_NAME}-profile \
  --role-name ${VM_NAME}-role

# Create a security group and allow SSH (port 22) and the HTTP server in a Docker container (port 8080)
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
  --port 8080 \
  --cidr 0.0.0.0/0

# Create a virtual machine and install Docker engine and AWS CLI using user data
INSTANCE_ID=$(aws ec2 run-instances \
  --region $REGION \
  --image-id $IMAGE \
  --instance-type $SIZE \
  --security-group-ids $SECURITY_GROUP_ID \
  --associate-public-ip-address \
  --iam-instance-profile Name=${VM_NAME}-profile \
  --user-data file://install-docker-aws-cli.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_NAME}]" \
  --query "Instances[0].InstanceId" \
  --output text)

aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID

# !!! Access the VM using EC2 Instance Connect, build and run the Docker image (see readme.md)

# Get public IP address
IP_ADDRESS=$(aws ec2 describe-instances \
  --region $REGION \
  --instance-ids $INSTANCE_ID \
  --query "Reservations[0].Instances[0].PublicIpAddress" \
  --output text)

curl --connect-timeout 5 http://$IP_ADDRESS:8080
