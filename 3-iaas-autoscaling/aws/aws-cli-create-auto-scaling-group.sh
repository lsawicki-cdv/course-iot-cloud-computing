#!/bin/bash

# Variables
REGION="eu-west-2"
SCALE_SET_NAME="my-scale-set"
IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
SIZE="t3.micro"

# Download the nginx installation script (passed to the VMs as user data)
curl -o vm.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh

# Get the default VPC and its subnets (one per availability zone)
VPC_ID=$(aws ec2 describe-vpcs \
  --region $REGION \
  --filters Name=is-default,Values=true \
  --query "Vpcs[0].VpcId" \
  --output text)

SUBNET_IDS=$(aws ec2 describe-subnets \
  --region $REGION \
  --filters Name=vpc-id,Values=$VPC_ID Name=default-for-az,Values=true \
  --query "join(',', Subnets[].SubnetId)" \
  --output text)

# Create a security group (used by the VMs and the load balancer) and allow SSH (port 22)
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name ${SCALE_SET_NAME}-sg \
  --description "Security group for $SCALE_SET_NAME" \
  --vpc-id $VPC_ID \
  --query GroupId \
  --output text)

aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

# Create a launch template that installs nginx server using user data
cat > launch-template.json <<EOF
{
  "ImageId": "$IMAGE",
  "InstanceType": "$SIZE",
  "SecurityGroupIds": ["$SECURITY_GROUP_ID"],
  "UserData": "$(base64 -w0 vm.sh)"
}
EOF

aws ec2 create-launch-template \
  --region $REGION \
  --launch-template-name ${SCALE_SET_NAME}-template \
  --launch-template-data file://launch-template.json

# Create a target group and a load balancer listening on the http port (80)
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
  --region $REGION \
  --name ${SCALE_SET_NAME}-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id $VPC_ID \
  --query "TargetGroups[0].TargetGroupArn" \
  --output text)

LOAD_BALANCER_ARN=$(aws elbv2 create-load-balancer \
  --region $REGION \
  --name ${SCALE_SET_NAME}-lb \
  --subnets ${SUBNET_IDS//,/ } \
  --security-groups $SECURITY_GROUP_ID \
  --query "LoadBalancers[0].LoadBalancerArn" \
  --output text)

aws elbv2 create-listener \
  --region $REGION \
  --load-balancer-arn $LOAD_BALANCER_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN

# Create an Auto Scaling group with fixed size
aws autoscaling create-auto-scaling-group \
  --region $REGION \
  --auto-scaling-group-name $SCALE_SET_NAME \
  --launch-template LaunchTemplateName=${SCALE_SET_NAME}-template \
  --min-size 2 \
  --max-size 2 \
  --desired-capacity 2 \
  --vpc-zone-identifier $SUBNET_IDS \
  --target-group-arns $TARGET_GROUP_ARN \
  --tags Key=Name,Value=$SCALE_SET_NAME,PropagateAtLaunch=true

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

# Wait until both VMs pass the load balancer health checks
aws elbv2 wait target-in-service --region $REGION --target-group-arn $TARGET_GROUP_ARN

# Get the DNS name of the load balancer
LB_ADDRESS=$(aws elbv2 describe-load-balancers \
  --region $REGION \
  --load-balancer-arns $LOAD_BALANCER_ARN \
  --query "LoadBalancers[0].DNSName" \
  --output text)

curl --connect-timeout 5 http://$LB_ADDRESS

# Delete all resources
# aws autoscaling delete-auto-scaling-group --region $REGION --auto-scaling-group-name $SCALE_SET_NAME --force-delete
# aws elbv2 delete-load-balancer --region $REGION --load-balancer-arn $LOAD_BALANCER_ARN
# aws elbv2 wait load-balancers-deleted --region $REGION --load-balancer-arns $LOAD_BALANCER_ARN
# aws ec2 wait instance-terminated --region $REGION --filters Name=tag:aws:autoscaling:groupName,Values=$SCALE_SET_NAME
# aws elbv2 delete-target-group --region $REGION --target-group-arn $TARGET_GROUP_ARN
# aws ec2 delete-launch-template --region $REGION --launch-template-name ${SCALE_SET_NAME}-template
# aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
