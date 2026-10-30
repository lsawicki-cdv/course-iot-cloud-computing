#!/bin/bash

# Variables
REGION="eu-west-2"
CONTAINER_NAME="my-container-test"
REPOSITORY_NAME="my-custom-app"
IMAGE_TAG="1.0.0"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Create a container registry repository to save the Docker image
aws ecr create-repository --region $REGION --repository-name $REPOSITORY_NAME

# !!! Push the Docker image to the repository from the VM (see readme.md)

# Create an IAM role that allows ECS to pull the Docker image from ECR
cat > ecs-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
EOF

EXECUTION_ROLE_ARN=$(aws iam create-role \
  --role-name ${CONTAINER_NAME}-execution-role \
  --assume-role-policy-document file://ecs-trust-policy.json \
  --query Role.Arn \
  --output text)

aws iam attach-role-policy \
  --role-name ${CONTAINER_NAME}-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create an ECS cluster
aws ecs create-cluster --region $REGION --cluster-name $CONTAINER_NAME

# Register a task definition (the container's image, CPU, memory and port)
cat > task-definition.json <<EOF
{
  "family": "$CONTAINER_NAME",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "$CONTAINER_NAME",
      "image": "$REGISTRY/$REPOSITORY_NAME:$IMAGE_TAG",
      "portMappings": [{"containerPort": 80}],
      "essential": true
    }
  ]
}
EOF

aws ecs register-task-definition --region $REGION --cli-input-json file://task-definition.json

# Create a security group that opens the http port (80)
CONTAINER_SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name ${CONTAINER_NAME}-sg \
  --description "Security group for $CONTAINER_NAME" \
  --query GroupId \
  --output text)

aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $CONTAINER_SECURITY_GROUP_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# Run the container on Fargate in a default subnet, with a public IP address
SUBNET_ID=$(aws ec2 describe-subnets \
  --region $REGION \
  --filters Name=default-for-az,Values=true \
  --query "Subnets[0].SubnetId" \
  --output text)

TASK_ARN=$(aws ecs run-task \
  --region $REGION \
  --cluster $CONTAINER_NAME \
  --launch-type FARGATE \
  --task-definition $CONTAINER_NAME \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$CONTAINER_SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
  --query "tasks[0].taskArn" \
  --output text)

aws ecs wait tasks-running --region $REGION --cluster $CONTAINER_NAME --tasks $TASK_ARN

# Get the public IP address of the container
NETWORK_INTERFACE_ID=$(aws ecs describe-tasks \
  --region $REGION \
  --cluster $CONTAINER_NAME \
  --tasks $TASK_ARN \
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" \
  --output text)

CONTAINER_IP_ADDRESS=$(aws ec2 describe-network-interfaces \
  --region $REGION \
  --network-interface-ids $NETWORK_INTERFACE_ID \
  --query "NetworkInterfaces[0].Association.PublicIp" \
  --output text)

# Test the container
curl --connect-timeout 5 http://$CONTAINER_IP_ADDRESS
