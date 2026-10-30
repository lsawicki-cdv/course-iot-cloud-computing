### AWS Elastic Container Service (Fargate)

This is the AWS version of the [Azure Container Instance task](../readme.md). It uses the same `Dockerfile` and `index.html`.

| Azure | AWS |
|-------|-----|
| Virtual Machine with the Docker extension | EC2 instance with Docker installed by user data |
| `az login` on the VM | IAM role attached to the VM (instance profile) - no login needed |
| Azure Container Registry (ACR) | Elastic Container Registry (ECR) repository |
| Azure Container Instances (ACI) | Elastic Container Service (ECS) task running on Fargate |
| `az container create` | ECS cluster + task definition + `aws ecs run-task` |
| `--dns-name-label` (DNS name of the container) | Public IP address of the task |
| Resource group | No direct equivalent - resources are deleted one by one |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. The EC2 instance (t3.micro) and the ECR repository (up to 500 MB) are Free Tier eligible. **ECS on Fargate is not in the legacy Free Tier**: on accounts created after July 2025 it is paid from your Free Tier credits, on older accounts it costs about $0.01 per hour for this task (0.25 vCPU, 0.5 GB). Stop the task and delete all resources at the end of the task.

1. Issue the following commands in **AWS CloudShell** (the terminal icon in the AWS Console's top bar)

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables
   ```bash
      REGION="eu-west-2"  # Change to another region if needed
   ```
   ```bash
      VM_NAME="my-vm-docker"
   ```
   ```bash
      IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
   ```
   ```bash
      SIZE="t3.micro"
   ```
   2. Download the `install-docker-aws-cli.sh` script, which will be passed to the virtual machine as user data (a script run on its first boot). It installs the Docker engine and the AWS CLI
   ```bash
   curl -o install-docker-aws-cli.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/4-iaas-containers/aws/install-docker-aws-cli.sh
   ```
   3. Create an IAM role that the virtual machine will use to push Docker images to the container registry. This replaces `az login` on the virtual machine: the AWS CLI on the virtual machine gets temporary credentials from the role
   ```bash
   cat > ec2-trust-policy.json <<EOF
   {
     "Version": "2012-10-17",
     "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
   }
   EOF
   ```
   ```bash
      aws iam create-role \
         --role-name ${VM_NAME}-role \
         --assume-role-policy-document file://ec2-trust-policy.json
   ```
   ```bash
      aws iam attach-role-policy \
         --role-name ${VM_NAME}-role \
         --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
   ```
   4. Create an instance profile, which attaches the IAM role to the virtual machine
   ```bash
      aws iam create-instance-profile --instance-profile-name ${VM_NAME}-profile
   ```
   ```bash
      aws iam add-role-to-instance-profile \
         --instance-profile-name ${VM_NAME}-profile \
         --role-name ${VM_NAME}-role
   ```
   5. Create a security group and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```bash
      SECURITY_GROUP_ID=$(aws ec2 create-security-group \
         --region $REGION \
         --group-name ${VM_NAME}-sg \
         --description "Security group for $VM_NAME" \
         --query GroupId \
         --output text)
   ```
   6. Allow SSH traffic (port 22), and open the 8080 port that will be used later by the HTTP server in a Docker container
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
         --port 8080 \
         --cidr 0.0.0.0/0
   ```
   7. Create a virtual machine with the IAM role, which installs the Docker engine and the AWS CLI from the user data, and save its ID to the terminal environmental variable `INSTANCE_ID`. If it fails with `Invalid IAM Instance Profile name`, the instance profile isn't ready yet: wait 10 seconds and try again
   ```bash
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
   ```

   **Option B: Using PowerShell**

   Start PowerShell in AWS CloudShell by typing `pwsh`.
   1. Set the terminal environmental variables (PowerShell syntax)
   ```powershell
      $REGION="eu-west-2"  # Change to another region if needed
   ```
   ```powershell
      $VM_NAME="my-vm-docker"
   ```
   ```powershell
      $IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
   ```
   ```powershell
      $SIZE="t3.micro"
   ```
   2. Download the `install-docker-aws-cli.sh` script, which will be passed to the virtual machine as user data (a script run on its first boot). It installs the Docker engine and the AWS CLI
   ```powershell
   curl -o install-docker-aws-cli.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/4-iaas-containers/aws/install-docker-aws-cli.sh
   ```
   3. Create an IAM role that the virtual machine will use to push Docker images to the container registry. This replaces `az login` on the virtual machine: the AWS CLI on the virtual machine gets temporary credentials from the role
   ```powershell
   @'
   {
     "Version": "2012-10-17",
     "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]
   }
   '@ | Set-Content ec2-trust-policy.json
   ```
   ```powershell
      aws iam create-role `
         --role-name "$VM_NAME-role" `
         --assume-role-policy-document file://ec2-trust-policy.json
   ```
   ```powershell
      aws iam attach-role-policy `
         --role-name "$VM_NAME-role" `
         --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
   ```
   4. Create an instance profile, which attaches the IAM role to the virtual machine
   ```powershell
      aws iam create-instance-profile --instance-profile-name "$VM_NAME-profile"
   ```
   ```powershell
      aws iam add-role-to-instance-profile `
         --instance-profile-name "$VM_NAME-profile" `
         --role-name "$VM_NAME-role"
   ```
   5. Create a security group and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```powershell
      $SECURITY_GROUP_ID=$(aws ec2 create-security-group `
         --region $REGION `
         --group-name "$VM_NAME-sg" `
         --description "Security group for $VM_NAME" `
         --query GroupId `
         --output text)
   ```
   6. Allow SSH traffic (port 22), and open the 8080 port that will be used later by the HTTP server in a Docker container
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
         --port 8080 `
         --cidr 0.0.0.0/0
   ```
   7. Create a virtual machine with the IAM role, which installs the Docker engine and the AWS CLI from the user data, and save its ID to the terminal environmental variable `INSTANCE_ID`. If it fails with `Invalid IAM Instance Profile name`, the instance profile isn't ready yet: wait 10 seconds and try again
   ```powershell
      $INSTANCE_ID=$(aws ec2 run-instances `
         --region $REGION `
         --image-id $IMAGE `
         --instance-type $SIZE `
         --security-group-ids $SECURITY_GROUP_ID `
         --associate-public-ip-address `
         --iam-instance-profile "Name=$VM_NAME-profile" `
         --user-data file://install-docker-aws-cli.sh `
         --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_NAME}]" `
         --query "Instances[0].InstanceId" `
         --output text)
   ```
2. Access the virtual machine in the AWS Console: EC2 → Instances → select `my-vm-docker` → "Connect" → "EC2 Instance Connect" → "Connect"
3. In the SSH of the Virtual Machine issue the following commands:
   1. Wait until the user data script has installed the Docker engine and the AWS CLI (it prints `status: done`)
   ```bash
      cloud-init status --wait
   ```
   2. Create Dockerfile
   ```bash
      nano Dockerfile
   ```
   3. Copy the following content to the terminal and save it on the virtual machine
   ```
      ARG UBUNTU_VERSION=22.04
      FROM ubuntu:${UBUNTU_VERSION} AS base

      # OS dependencies and packages
      RUN apt-get update && \
         apt-get install nginx --no-install-recommends -y \
         && rm -rf /var/lib/apt/lists/*

      EXPOSE 80
      WORKDIR /var/www/html

      COPY index.html /var/www/html/index.html

      CMD [ "nginx", "-g", "daemon off;" ]
   ```
   4. Create HTML file
   ```bash
      nano index.html
   ```
   5. Copy the following content to the terminal and save it on the virtual machine
   ```
      <h1>Hello World from Docker!</h1>
   ```
   6. The user data script has already added the `ubuntu` user to the `docker` group. Close the EC2 Instance Connect window and connect once again, so the group membership takes effect
   7. Build the Docker image from the `Dockerfile`
   ```bash
      docker build -t my-custom-app:1.0.0 .
   ```
   8. Run the Docker container with the Docker image that was build in the previous step `my-custom-app:1.0.0`
   ```bash
      docker run --rm -p 8080:80 my-custom-app:1.0.0 &
   ```
4. Check in the web browser or using `curl` that the HTTP traffic goes to the Docker container on the EC2 instance on port 8080 (`http://<public IPv4 address>:8080`, the address is shown in EC2 → Instances)
5. Create a container registry repository for the Docker image. In **AWS CloudShell** issue the following commands (the same in Bash and PowerShell; in PowerShell add `$` before the variable name: `$REPOSITORY_NAME="my-custom-app"`)
   ```bash
      REPOSITORY_NAME="my-custom-app"
   ```
   ```bash
      aws ecr create-repository --region $REGION --repository-name $REPOSITORY_NAME
   ```
6. Push the Docker image to the repository. In **the SSH of the Virtual Machine** issue the following commands
   1. Set the terminal environmental variables
   ```bash
      REGION="eu-west-2"  # Change to another region if needed
   ```
   ```bash
      REPOSITORY_NAME="my-custom-app"
   ```
   ```bash
      IMAGE_TAG="1.0.0"
   ```
   ```bash
      ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ```
   ```bash
      REGISTRY="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
   ```
   2. Log in to the container registry (the AWS CLI uses the IAM role of the virtual machine, so there is no `aws login` step)
   ```bash
      aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY
   ```
   3. Push the Docker image to the repository
   ```bash
      docker tag my-custom-app:$IMAGE_TAG $REGISTRY/$REPOSITORY_NAME:$IMAGE_TAG
      docker push $REGISTRY/$REPOSITORY_NAME:$IMAGE_TAG
   ```
   4. Check if the container image is available in the AWS Console: Elastic Container Registry → Repositories → `my-custom-app`
7. Run the same Docker image using ECS on Fargate. In **AWS CloudShell** issue the following commands

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables
   ```bash
      CONTAINER_NAME="my-container-test"
   ```
   ```bash
      IMAGE_TAG="1.0.0"
   ```
   ```bash
      ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ```
   ```bash
      REGISTRY="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
   ```
   2. Create an IAM role that allows ECS to pull the Docker image from the repository (the task execution role), and save its ARN to the terminal environmental variable `EXECUTION_ROLE_ARN`
   ```bash
   cat > ecs-trust-policy.json <<EOF
   {
     "Version": "2012-10-17",
     "Statement": [{"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"}, "Action": "sts:AssumeRole"}]
   }
   EOF
   ```
   ```bash
      EXECUTION_ROLE_ARN=$(aws iam create-role \
         --role-name ${CONTAINER_NAME}-execution-role \
         --assume-role-policy-document file://ecs-trust-policy.json \
         --query Role.Arn \
         --output text)
   ```
   ```bash
      aws iam attach-role-policy \
         --role-name ${CONTAINER_NAME}-execution-role \
         --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
   ```
   3. Create an ECS cluster (a logical group for running containers; with Fargate there are no virtual machines to manage)
   ```bash
      aws ecs create-cluster --region $REGION --cluster-name $CONTAINER_NAME
   ```
   4. Register a task definition, which describes the container: its image, CPU, memory and port
   ```bash
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
   ```
   ```bash
      aws ecs register-task-definition --region $REGION --cli-input-json file://task-definition.json
   ```
   5. Create a security group for the container that opens the http port (80), and save its ID to the terminal environmental variable `CONTAINER_SECURITY_GROUP_ID`
   ```bash
      CONTAINER_SECURITY_GROUP_ID=$(aws ec2 create-security-group \
         --region $REGION \
         --group-name ${CONTAINER_NAME}-sg \
         --description "Security group for $CONTAINER_NAME" \
         --query GroupId \
         --output text)
   ```
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $CONTAINER_SECURITY_GROUP_ID \
         --protocol tcp \
         --port 80 \
         --cidr 0.0.0.0/0
   ```
   6. Get the ID of a default subnet and save it to the terminal environmental variable `SUBNET_ID`
   ```bash
      SUBNET_ID=$(aws ec2 describe-subnets \
         --region $REGION \
         --filters Name=default-for-az,Values=true \
         --query "Subnets[0].SubnetId" \
         --output text)
   ```
   7. Run the container on Fargate with a public IP address, and save the task's ARN to the terminal environmental variable `TASK_ARN`
   ```bash
      TASK_ARN=$(aws ecs run-task \
         --region $REGION \
         --cluster $CONTAINER_NAME \
         --launch-type FARGATE \
         --task-definition $CONTAINER_NAME \
         --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$CONTAINER_SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
         --query "tasks[0].taskArn" \
         --output text)
   ```
   8. Wait until the container is running
   ```bash
      aws ecs wait tasks-running --region $REGION --cluster $CONTAINER_NAME --tasks $TASK_ARN
   ```
   9. Get the public IP address of the container (through the task's network interface) and save it to the terminal environmental variable `CONTAINER_IP_ADDRESS`
   ```bash
      NETWORK_INTERFACE_ID=$(aws ecs describe-tasks \
         --region $REGION \
         --cluster $CONTAINER_NAME \
         --tasks $TASK_ARN \
         --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" \
         --output text)
   ```
   ```bash
      CONTAINER_IP_ADDRESS=$(aws ec2 describe-network-interfaces \
         --region $REGION \
         --network-interface-ids $NETWORK_INTERFACE_ID \
         --query "NetworkInterfaces[0].Association.PublicIp" \
         --output text)
   ```

   **Option B: Using PowerShell**
   1. Set the terminal environmental variables (PowerShell syntax)
   ```powershell
      $CONTAINER_NAME="my-container-test"
   ```
   ```powershell
      $IMAGE_TAG="1.0.0"
   ```
   ```powershell
      $ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   ```
   ```powershell
      $REGISTRY="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
   ```
   2. Create an IAM role that allows ECS to pull the Docker image from the repository (the task execution role), and save its ARN to the terminal environmental variable `EXECUTION_ROLE_ARN`
   ```powershell
   @'
   {
     "Version": "2012-10-17",
     "Statement": [{"Effect": "Allow", "Principal": {"Service": "ecs-tasks.amazonaws.com"}, "Action": "sts:AssumeRole"}]
   }
   '@ | Set-Content ecs-trust-policy.json
   ```
   ```powershell
      $EXECUTION_ROLE_ARN=$(aws iam create-role `
         --role-name "$CONTAINER_NAME-execution-role" `
         --assume-role-policy-document file://ecs-trust-policy.json `
         --query Role.Arn `
         --output text)
   ```
   ```powershell
      aws iam attach-role-policy `
         --role-name "$CONTAINER_NAME-execution-role" `
         --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
   ```
   3. Create an ECS cluster (a logical group for running containers; with Fargate there are no virtual machines to manage)
   ```powershell
      aws ecs create-cluster --region $REGION --cluster-name $CONTAINER_NAME
   ```
   4. Register a task definition, which describes the container: its image, CPU, memory and port
   ```powershell
   @"
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
         "image": "$REGISTRY/${REPOSITORY_NAME}:$IMAGE_TAG",
         "portMappings": [{"containerPort": 80}],
         "essential": true
       }
     ]
   }
   "@ | Set-Content task-definition.json
   ```
   ```powershell
      aws ecs register-task-definition --region $REGION --cli-input-json file://task-definition.json
   ```
   5. Create a security group for the container that opens the http port (80), and save its ID to the terminal environmental variable `CONTAINER_SECURITY_GROUP_ID`
   ```powershell
      $CONTAINER_SECURITY_GROUP_ID=$(aws ec2 create-security-group `
         --region $REGION `
         --group-name "$CONTAINER_NAME-sg" `
         --description "Security group for $CONTAINER_NAME" `
         --query GroupId `
         --output text)
   ```
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $CONTAINER_SECURITY_GROUP_ID `
         --protocol tcp `
         --port 80 `
         --cidr 0.0.0.0/0
   ```
   6. Get the ID of a default subnet and save it to the terminal environmental variable `SUBNET_ID`
   ```powershell
      $SUBNET_ID=$(aws ec2 describe-subnets `
         --region $REGION `
         --filters Name=default-for-az,Values=true `
         --query "Subnets[0].SubnetId" `
         --output text)
   ```
   7. Run the container on Fargate with a public IP address, and save the task's ARN to the terminal environmental variable `TASK_ARN`
   ```powershell
      $TASK_ARN=$(aws ecs run-task `
         --region $REGION `
         --cluster $CONTAINER_NAME `
         --launch-type FARGATE `
         --task-definition $CONTAINER_NAME `
         --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$CONTAINER_SECURITY_GROUP_ID],assignPublicIp=ENABLED}" `
         --query "tasks[0].taskArn" `
         --output text)
   ```
   8. Wait until the container is running
   ```powershell
      aws ecs wait tasks-running --region $REGION --cluster $CONTAINER_NAME --tasks $TASK_ARN
   ```
   9. Get the public IP address of the container (through the task's network interface) and save it to the terminal environmental variable `CONTAINER_IP_ADDRESS`
   ```powershell
      $NETWORK_INTERFACE_ID=$(aws ecs describe-tasks `
         --region $REGION `
         --cluster $CONTAINER_NAME `
         --tasks $TASK_ARN `
         --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" `
         --output text)
   ```
   ```powershell
      $CONTAINER_IP_ADDRESS=$(aws ec2 describe-network-interfaces `
         --region $REGION `
         --network-interface-ids $NETWORK_INTERFACE_ID `
         --query "NetworkInterfaces[0].Association.PublicIp" `
         --output text)
   ```
8. Check in the web browser or using `curl` that the HTTP traffic goes to the Docker container running on Fargate on port 80
   ```bash
      curl --connect-timeout 5 http://$CONTAINER_IP_ADDRESS
   ```
9. Delete all resources. AWS has no resource groups, so delete them one by one in **AWS CloudShell**, in this order (the same commands work in Bash and PowerShell)
   1. Stop the container and delete the ECS resources
   ```bash
   aws ecs stop-task --region $REGION --cluster $CONTAINER_NAME --task $TASK_ARN
   ```
   ```bash
   aws ecs wait tasks-stopped --region $REGION --cluster $CONTAINER_NAME --tasks $TASK_ARN
   ```
   ```bash
   aws ecs deregister-task-definition --region $REGION --task-definition "${CONTAINER_NAME}:1"
   ```
   ```bash
   aws ecs delete-cluster --region $REGION --cluster $CONTAINER_NAME
   ```
   2. Delete the repository together with the Docker image
   ```bash
   aws ecr delete-repository --region $REGION --repository-name $REPOSITORY_NAME --force
   ```
   3. Terminate the virtual machine
   ```bash
   aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID
   ```
   ```bash
   aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID
   ```
   4. Delete the security groups. If it fails with `DependencyViolation`, the network interface of the container isn't released yet: wait a minute and try again
   ```bash
   aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
   ```
   ```bash
   aws ec2 delete-security-group --region $REGION --group-id $CONTAINER_SECURITY_GROUP_ID
   ```
   5. Delete the IAM roles and the instance profile
   ```bash
   aws iam remove-role-from-instance-profile --instance-profile-name "${VM_NAME}-profile" --role-name "${VM_NAME}-role"
   ```
   ```bash
   aws iam delete-instance-profile --instance-profile-name "${VM_NAME}-profile"
   ```
   ```bash
   aws iam detach-role-policy --role-name "${VM_NAME}-role" --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
   ```
   ```bash
   aws iam delete-role --role-name "${VM_NAME}-role"
   ```
   ```bash
   aws iam detach-role-policy --role-name "${CONTAINER_NAME}-execution-role" --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
   ```
   ```bash
   aws iam delete-role --role-name "${CONTAINER_NAME}-execution-role"
   ```
