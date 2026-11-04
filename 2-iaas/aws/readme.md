### AWS Virtual Machine (EC2) task

This is the AWS version of the [Azure Virtual Machine task](../readme.md). It uses the same `vm.sh` script to install nginx.

| Azure | AWS |
|-------|-----|
| Virtual Machine | EC2 instance |
| Resource group | No direct equivalent - resources are tagged and deleted one by one |
| Network security group (NSG) | Security group |
| Custom Script Extension | User data |
| Azure Cloud Shell | AWS CloudShell |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region and only Free Tier eligible resources. Remember to delete the resources at the end of the task, so you don't use up your Free Tier credits.

1. Create an EC2 instance from the AWS Console: https://console.aws.amazon.com/ec2/home#LaunchInstances:
   1. Region: Europe (London) (or your allowed region), selected in the top-right corner of the Console
   2. Name: `my-vm`
   3. Image (AMI): Ubuntu Server 26.04 LTS
   4. Instance type: t3.micro (Free Tier eligible; use t2.micro if t3.micro isn't eligible in your region)
   5. Key pair: Proceed without a key pair (we will connect using EC2 Instance Connect)
   6. Network settings: Allow SSH traffic from Anywhere (port 22)
   7. Click "Launch instance"
2. Wait until the instance state is "Running"
3. Access the instance: select it, click "Connect", choose the "EC2 Instance Connect" tab and click "Connect"
4. Issue the following commands to the VM from the `vm.sh` script and install nginx server
```bash
# Use this for your user data (script from top to bottom)
# install httpd (Linux 2 version)
sudo apt update -y
# install ngnix server
sudo apt install nginx -y
# start ngnix server
sudo systemctl start nginx
# enable ngnix server
sudo systemctl enable nginx
# change welcome page to custom page
echo "<h1>Hello World from $(hostname -f)</h1>" | sudo tee /var/www/html/index.html
```
5. Try to access the VM using its public IPv4 address via the Browser, using `http://` (you shouldn't have access)
6. Add an inbound rule to the instance's security group to allow HTTP traffic (port 80): in the "Security" tab, click the security group, then "Edit inbound rules" → "Add rule" → Type: HTTP, Source: Anywhere-IPv4
7. Try again to access the VM using its public IP address via the Browser (you should have access)
8. Terminate the instance ("Instance state" → "Terminate instance") and delete its security group (EC2 → Security Groups)
9. Issue the following commands in **AWS CloudShell** (the terminal icon in the AWS Console's top bar)

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables
   ```bash
   REGION="eu-west-2"
   ```
   ```bash
   VM_NAME="my-vm"
   ```
   ```bash
   SECURITY_GROUP_NAME="my-vm-sg"
   ```
   ```bash
   IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
   ```
   ```bash
   SIZE="t3.micro"
   ```
   2. Download the `vm.sh` script, which will be passed to the virtual machine as user data (a script run on its first boot)
   ```bash
   curl -o vm.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh
   ```
   3. Create a security group in the default VPC and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```bash
      SECURITY_GROUP_ID=$(aws ec2 create-security-group \
         --region $REGION \
         --group-name $SECURITY_GROUP_NAME \
         --description "Security group for $VM_NAME" \
         --query GroupId \
         --output text)
   ```
   4. Allow SSH traffic (port 22), like the Azure VM does by default
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $SECURITY_GROUP_ID \
         --protocol tcp \
         --port 22 \
         --cidr 0.0.0.0/0
   ```
   5. Create a virtual machine that installs nginx server from the user data, and save its ID to the terminal environmental variable `INSTANCE_ID`
   ```bash
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
   ```
   6. Wait until the virtual machine is running
   ```bash
      aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
   ```
   7. List the security group rules
   ```bash
      aws ec2 describe-security-group-rules \
         --region $REGION \
         --filters Name=group-id,Values=$SECURITY_GROUP_ID \
         --output table
   ```
   8. Create a security group rule to open the http port (80)
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $SECURITY_GROUP_ID \
         --protocol tcp \
         --port 80 \
         --cidr 0.0.0.0/0
   ```
   9. Get the public IP address of the virtual machine and save it to the terminal environmental variable `IP_ADDRESS`
   ```bash
      IP_ADDRESS=$(aws ec2 describe-instances \
         --region $REGION \
         --instance-ids $INSTANCE_ID \
         --query "Reservations[0].Instances[0].PublicIpAddress" \
         --output text)
   ```
   10. Check connection to the HTTP server running on the virtual machine (the user data script needs a minute or two after boot; retry if the connection times out)
   ```bash
      curl --connect-timeout 5 http://$IP_ADDRESS
   ```

   **Option B: Using PowerShell**

   Start PowerShell in AWS CloudShell by typing `pwsh`.
   1. Set the terminal environmental variables (PowerShell syntax)
   ```powershell
   $REGION="eu-west-2"
   ```
   ```powershell
   $VM_NAME="my-vm"
   ```
   ```powershell
   $SECURITY_GROUP_NAME="my-vm-sg"
   ```
   ```powershell
   $IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
   ```
   ```powershell
   $SIZE="t3.micro"
   ```
   2. Download the `vm.sh` script, which will be passed to the virtual machine as user data (a script run on its first boot)
   ```powershell
   curl -o vm.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh
   ```
   3. Create a security group in the default VPC and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```powershell
      $SECURITY_GROUP_ID=$(aws ec2 create-security-group `
         --region $REGION `
         --group-name $SECURITY_GROUP_NAME `
         --description "Security group for $VM_NAME" `
         --query GroupId `
         --output text)
   ```
   4. Allow SSH traffic (port 22), like the Azure VM does by default
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $SECURITY_GROUP_ID `
         --protocol tcp `
         --port 22 `
         --cidr 0.0.0.0/0
   ```
   5. Create a virtual machine that installs nginx server from the user data, and save its ID to the terminal environmental variable `INSTANCE_ID`
   ```powershell
      $INSTANCE_ID=$(aws ec2 run-instances `
         --region $REGION `
         --image-id $IMAGE `
         --instance-type $SIZE `
         --security-group-ids $SECURITY_GROUP_ID `
         --associate-public-ip-address `
         --user-data file://vm.sh `
         --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$VM_NAME}]" `
         --query "Instances[0].InstanceId" `
         --output text)
   ```
   6. Wait until the virtual machine is running
   ```powershell
      aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
   ```
   7. List the security group rules
   ```powershell
      aws ec2 describe-security-group-rules `
         --region $REGION `
         --filters Name=group-id,Values=$SECURITY_GROUP_ID `
         --output table
   ```
   8. Create a security group rule to open the http port (80)
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $SECURITY_GROUP_ID `
         --protocol tcp `
         --port 80 `
         --cidr 0.0.0.0/0
   ```
   9. Get the public IP address of the virtual machine and save it to the terminal environmental variable `IP_ADDRESS`
   ```powershell
      $IP_ADDRESS=$(aws ec2 describe-instances `
         --region $REGION `
         --instance-ids $INSTANCE_ID `
         --query "Reservations[0].Instances[0].PublicIpAddress" `
         --output text)
   ```
   10. Check connection to the HTTP server running on the virtual machine (the user data script needs a minute or two after boot; retry if the connection times out)
   ```powershell
      curl --connect-timeout 5 http://$IP_ADDRESS
   ```
10. Delete all resources (AWS has no resource groups, so terminate the instance first, then delete its security group)
   ```bash
   aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID
   ```
   ```bash
   aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID
   ```
   ```bash
   aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
   ```
