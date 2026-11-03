### AWS Auto Scaling group task

This is the AWS version of the [Azure Virtual Machine Scale Set task](../readme.md). It uses the `2-iaas/vm.sh` script to install nginx.

| Azure | AWS |
|-------|-----|
| Virtual Machine Scale Set | Auto Scaling group + launch template |
| Load balancer (created with the scale set) | Application Load Balancer + target group + listener (created separately) |
| Load balancer public IP address | Load balancer DNS name |
| Network security group (NSG) | Security group |
| Custom Script Extension | User data (set in the launch template) |
| Resource group | No direct equivalent - resources are deleted one by one |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region and only Free Tier eligible resources: two t3.micro instances and one Application Load Balancer. Both use Free Tier hours (or credits) for every hour they run, so delete all resources at the end of the task.

1. Open AWS CloudShell (the terminal icon in the AWS Console's top bar)
2. Issue the following commands in **AWS CloudShell**

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables
   ```bash
      REGION="eu-west-2"  # Change to another region if needed
   ```
   ```bash
      SCALE_SET_NAME="my-scale-set"
   ```
   ```bash
      IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
   ```
   ```bash
      SIZE="t3.micro"
   ```
   2. Download the `vm.sh` script, which will be passed to the virtual machines as user data (a script run on their first boot)
   ```bash
   curl -o vm.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh
   ```
   3. Get the ID of the default VPC (virtual network) and save it to the terminal environmental variable `VPC_ID`
   ```bash
      VPC_ID=$(aws ec2 describe-vpcs \
         --region $REGION \
         --filters Name=is-default,Values=true \
         --query "Vpcs[0].VpcId" \
         --output text)
   ```
   4. Get the IDs of its subnets (one per availability zone) and save them to the terminal environmental variable `SUBNET_IDS`
   ```bash
      SUBNET_IDS=$(aws ec2 describe-subnets \
         --region $REGION \
         --filters Name=vpc-id,Values=$VPC_ID Name=default-for-az,Values=true \
         --query "join(',', Subnets[].SubnetId)" \
         --output text)
   ```
   5. Create a security group for the virtual machines and the load balancer, and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```bash
      SECURITY_GROUP_ID=$(aws ec2 create-security-group \
         --region $REGION \
         --group-name ${SCALE_SET_NAME}-sg \
         --description "Security group for $SCALE_SET_NAME" \
         --vpc-id $VPC_ID \
         --query GroupId \
         --output text)
   ```
   6. Allow SSH traffic (port 22), like the Azure scale set does by default
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $SECURITY_GROUP_ID \
         --protocol tcp \
         --port 22 \
         --cidr 0.0.0.0/0
   ```
   7. Create a launch template, which describes the virtual machines of the Auto Scaling group. Its user data installs nginx server
   ```bash
   cat > launch-template.json <<EOF
   {
     "ImageId": "$IMAGE",
     "InstanceType": "$SIZE",
     "SecurityGroupIds": ["$SECURITY_GROUP_ID"],
     "UserData": "$(base64 -w0 vm.sh)"
   }
   EOF
   ```
   ```bash
      aws ec2 create-launch-template \
         --region $REGION \
         --launch-template-name ${SCALE_SET_NAME}-template \
         --launch-template-data file://launch-template.json
   ```
   8. Create a target group (the load balancer's backend pool) and save its ARN to the terminal environmental variable `TARGET_GROUP_ARN`
   ```bash
      TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
         --region $REGION \
         --name ${SCALE_SET_NAME}-tg \
         --protocol HTTP \
         --port 80 \
         --vpc-id $VPC_ID \
         --query "TargetGroups[0].TargetGroupArn" \
         --output text)
   ```
   9. Create an Application Load Balancer and save its ARN to the terminal environmental variable `LOAD_BALANCER_ARN`
   ```bash
      LOAD_BALANCER_ARN=$(aws elbv2 create-load-balancer \
         --region $REGION \
         --name ${SCALE_SET_NAME}-lb \
         --subnets ${SUBNET_IDS//,/ } \
         --security-groups $SECURITY_GROUP_ID \
         --query "LoadBalancers[0].LoadBalancerArn" \
         --output text)
   ```
   10. Create a listener (the load balancing rule) that forwards the http port (80) to the target group
   ```bash
      aws elbv2 create-listener \
         --region $REGION \
         --load-balancer-arn $LOAD_BALANCER_ARN \
         --protocol HTTP \
         --port 80 \
         --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
   ```
   11. Create an Auto Scaling group with two virtual machines, registered in the target group
   ```bash
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
   ```
   12. List the security group rules
   ```bash
      aws ec2 describe-security-group-rules \
         --region $REGION \
         --filters Name=group-id,Values=$SECURITY_GROUP_ID \
         --output table
   ```
   13. Create a security group rule to open the http port (80)
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $SECURITY_GROUP_ID \
         --protocol tcp \
         --port 80 \
         --cidr 0.0.0.0/0
   ```
   14. Wait until both virtual machines pass the load balancer health checks (it can take a few minutes)
   ```bash
      aws elbv2 wait target-in-service --region $REGION --target-group-arn $TARGET_GROUP_ARN
   ```
   15. Get the DNS name of the load balancer and save it to the terminal environmental variable `LB_ADDRESS`
   ```bash
      LB_ADDRESS=$(aws elbv2 describe-load-balancers \
         --region $REGION \
         --load-balancer-arns $LOAD_BALANCER_ARN \
         --query "LoadBalancers[0].DNSName" \
         --output text)
   ```
   16. Check connection to the HTTP server running on both virtual machines
   ```bash
      curl --connect-timeout 5 http://$LB_ADDRESS
   ```

   **Option B: Using PowerShell**

   Start PowerShell in AWS CloudShell by typing `pwsh`.
   1. Set the terminal environmental variables (PowerShell syntax)
   ```powershell
      $REGION="eu-west-2"  # Change to another region if needed
   ```
   ```powershell
      $SCALE_SET_NAME="my-scale-set"
   ```
   ```powershell
      $IMAGE="resolve:ssm:/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
   ```
   ```powershell
      $SIZE="t3.micro"
   ```
   2. Download the `vm.sh` script, which will be passed to the virtual machines as user data (a script run on their first boot)
   ```powershell
   curl -o vm.sh https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh
   ```
   3. Get the ID of the default VPC (virtual network) and save it to the terminal environmental variable `VPC_ID`
   ```powershell
      $VPC_ID=$(aws ec2 describe-vpcs `
         --region $REGION `
         --filters Name=is-default,Values=true `
         --query "Vpcs[0].VpcId" `
         --output text)
   ```
   4. Get the IDs of its subnets (one per availability zone) and save them to the terminal environmental variable `SUBNET_IDS`
   ```powershell
      $SUBNET_IDS=$(aws ec2 describe-subnets `
         --region $REGION `
         --filters Name=vpc-id,Values=$VPC_ID Name=default-for-az,Values=true `
         --query "join(',', Subnets[].SubnetId)" `
         --output text)
   ```
   5. Create a security group for the virtual machines and the load balancer, and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```powershell
      $SECURITY_GROUP_ID=$(aws ec2 create-security-group `
         --region $REGION `
         --group-name "$SCALE_SET_NAME-sg" `
         --description "Security group for $SCALE_SET_NAME" `
         --vpc-id $VPC_ID `
         --query GroupId `
         --output text)
   ```
   6. Allow SSH traffic (port 22), like the Azure scale set does by default
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $SECURITY_GROUP_ID `
         --protocol tcp `
         --port 22 `
         --cidr 0.0.0.0/0
   ```
   7. Create a launch template, which describes the virtual machines of the Auto Scaling group. Its user data installs nginx server
   ```powershell
   @{
     ImageId = $IMAGE
     InstanceType = $SIZE
     SecurityGroupIds = @($SECURITY_GROUP_ID)
     UserData = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$PWD/vm.sh"))
   } | ConvertTo-Json | Set-Content launch-template.json
   ```
   ```powershell
      aws ec2 create-launch-template `
         --region $REGION `
         --launch-template-name "$SCALE_SET_NAME-template" `
         --launch-template-data file://launch-template.json
   ```
   8. Create a target group (the load balancer's backend pool) and save its ARN to the terminal environmental variable `TARGET_GROUP_ARN`
   ```powershell
      $TARGET_GROUP_ARN=$(aws elbv2 create-target-group `
         --region $REGION `
         --name "$SCALE_SET_NAME-tg" `
         --protocol HTTP `
         --port 80 `
         --vpc-id $VPC_ID `
         --query "TargetGroups[0].TargetGroupArn" `
         --output text)
   ```
   9. Create an Application Load Balancer and save its ARN to the terminal environmental variable `LOAD_BALANCER_ARN`
   ```powershell
      $LOAD_BALANCER_ARN=$(aws elbv2 create-load-balancer `
         --region $REGION `
         --name "$SCALE_SET_NAME-lb" `
         --subnets ($SUBNET_IDS -split ',') `
         --security-groups $SECURITY_GROUP_ID `
         --query "LoadBalancers[0].LoadBalancerArn" `
         --output text)
   ```
   10. Create a listener (the load balancing rule) that forwards the http port (80) to the target group
   ```powershell
      aws elbv2 create-listener `
         --region $REGION `
         --load-balancer-arn $LOAD_BALANCER_ARN `
         --protocol HTTP `
         --port 80 `
         --default-actions "Type=forward,TargetGroupArn=$TARGET_GROUP_ARN"
   ```
   11. Create an Auto Scaling group with two virtual machines, registered in the target group
   ```powershell
      aws autoscaling create-auto-scaling-group `
         --region $REGION `
         --auto-scaling-group-name $SCALE_SET_NAME `
         --launch-template "LaunchTemplateName=$SCALE_SET_NAME-template" `
         --min-size 2 `
         --max-size 2 `
         --desired-capacity 2 `
         --vpc-zone-identifier $SUBNET_IDS `
         --target-group-arns $TARGET_GROUP_ARN `
         --tags "Key=Name,Value=$SCALE_SET_NAME,PropagateAtLaunch=true"
   ```
   12. List the security group rules
   ```powershell
      aws ec2 describe-security-group-rules `
         --region $REGION `
         --filters Name=group-id,Values=$SECURITY_GROUP_ID `
         --output table
   ```
   13. Create a security group rule to open the http port (80)
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $SECURITY_GROUP_ID `
         --protocol tcp `
         --port 80 `
         --cidr 0.0.0.0/0
   ```
   14. Wait until both virtual machines pass the load balancer health checks (it can take a few minutes)
   ```powershell
      aws elbv2 wait target-in-service --region $REGION --target-group-arn $TARGET_GROUP_ARN
   ```
   15. Get the DNS name of the load balancer and save it to the terminal environmental variable `LB_ADDRESS`
   ```powershell
      $LB_ADDRESS=$(aws elbv2 describe-load-balancers `
         --region $REGION `
         --load-balancer-arns $LOAD_BALANCER_ARN `
         --query "LoadBalancers[0].DNSName" `
         --output text)
   ```
   16. Check connection to the HTTP server running on both virtual machines
   ```powershell
      curl --connect-timeout 5 http://$LB_ADDRESS
   ```
3. Try to prove that the HTTP traffic goes to both virtual machines (the "Hello World from" text should be different in the browser; run `curl` a few times)
4. Delete all resources (AWS has no resource groups, so delete them one by one, in this order; the same commands work in Bash and PowerShell)
   ```bash
   aws autoscaling delete-auto-scaling-group --region $REGION --auto-scaling-group-name $SCALE_SET_NAME --force-delete
   ```
   ```bash
   aws elbv2 delete-load-balancer --region $REGION --load-balancer-arn $LOAD_BALANCER_ARN
   ```
   ```bash
   aws elbv2 wait load-balancers-deleted --region $REGION --load-balancer-arns $LOAD_BALANCER_ARN
   ```
   ```bash
   aws ec2 wait instance-terminated --region $REGION --filters Name=tag:aws:autoscaling:groupName,Values=$SCALE_SET_NAME
   ```
   ```bash
   aws elbv2 delete-target-group --region $REGION --target-group-arn $TARGET_GROUP_ARN
   ```
   ```bash
   aws ec2 delete-launch-template --region $REGION --launch-template-name "$SCALE_SET_NAME-template"
   ```
   ```bash
   aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
   ```
   If deleting the target group fails with `ResourceInUse`, or deleting the security group fails with `DependencyViolation`, AWS is still removing the load balancer's listener or network interfaces. Wait a minute and try again.
5. Do the same however using the AWS Console, not the AWS CLI
   1. Region: Europe (London) (or another region), selected in the top-right corner of the Console
   2. Go to EC2 → Launch Templates → "Create launch template"
      1. Name: `my-scale-set-template`
      2. Image (AMI): Ubuntu Server 22.04 LTS
      3. Instance type: t3.micro
      4. Key pair: Don't include in launch template (we will connect using EC2 Instance Connect)
      5. Network settings: create a security group that allows SSH traffic (port 22) from anywhere
      6. Click "Create launch template"
   3. Go to EC2 → Auto Scaling Groups → "Create Auto Scaling group"
      1. Name: `my-scale-set`, launch template: `my-scale-set-template`
      2. Network: default VPC, select all availability zones
      3. Load balancing: "Attach to a new load balancer" → Application Load Balancer, Internet-facing, create a new target group on port 80
      4. Desired, minimum and maximum capacity: 2
      5. Click "Create Auto Scaling group"
   4. Go to EC2 → Security Groups, open the security group of the launch template and add an inbound rule for HTTP traffic (port 80) from Anywhere-IPv4
   5. Go to EC2 → Load Balancers, open the new load balancer and add the same security group to it ("Security" tab → "Edit")
   6. Go to each virtual machine (EC2 → Instances) and access it using "Connect" → "EC2 Instance Connect"
   7. Issue commands to the VM from the `2-iaas/vm.sh` script and install nginx server
   8. Open the load balancer's DNS name in the browser (`http://`)
6. Delete all resources: the Auto Scaling group, the load balancer, the target group, the launch template and the security group
