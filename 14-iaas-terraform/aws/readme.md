# AWS Virtual Machine (EC2) with Terraform

This is the AWS version of the [Azure Terraform exercise](../readme.md). You'll deploy a complete Linux VM infrastructure on AWS with **Terraform**, including networking, security, and automated web server installation - with the same Terraform workflow, the same SSH key module and the same nginx script as the Azure version.

| Azure | AWS |
|-------|-----|
| `azurerm` provider | `aws` provider |
| Resource group (`azurerm_resource_group`) | No direct equivalent - Terraform's state lists everything it created; the provider tags all resources with `Project = terraform-vm` |
| Virtual network + subnet | VPC + subnet (`aws_vpc`, `aws_subnet`) |
| Internet access built into the virtual network | Internet gateway + route table (`aws_internet_gateway`, `aws_route_table`) |
| Public IP address (`azurerm_public_ip`) | Public IP of the subnet (`map_public_ip_on_launch`) |
| Network security group (`security_rule`) | Security group (`ingress` / `egress`) |
| Network interface (`azurerm_network_interface`) | Created with the instance automatically |
| Linux virtual machine (`Standard_B1s`) | EC2 instance (`t3.micro`) |
| Image `Canonical:ubuntu-26_04-lts:server:latest` | AMI from the SSM parameter of Canonical (`data "aws_ssm_parameter"`) |
| SSH public key on the VM (`admin_ssh_key`) | EC2 key pair (`aws_key_pair`) |
| Admin user `azureadmin` (your choice) | User `ubuntu` (fixed by the image) |
| `custom_data` (base64) | `user_data` (plain text) |
| Boot diagnostics | EC2 serial console / **Get system log** |
| Azure Cloud Shell (Terraform pre-installed) | AWS CloudShell (install Terraform yourself) |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. If your account is limited to one region (for example a new AWS account with a selected Region), use that region instead (`-var region=<region>`, see Step 7). Everything in this exercise is Free Tier eligible: a `t3.micro` instance (750 hours per month), its disk and its public IPv4 address; VPCs, subnets, internet gateways, route tables and security groups are free. Destroy everything at the end of the exercise.

**Read first:** [Terraform Basics](../terraform-basics.md) - what Terraform is, how this exercise is organized, the workflow and the state. That page is shared with the Azure version; this readme contains only the AWS steps.

## Architecture Overview

This Terraform configuration deploys a complete VM infrastructure:

```
VPC (10.0.0.0/16)
  ├── Subnet (10.0.1.0/24, public IP addresses on)
  ├── Internet Gateway
  ├── Route Table (0.0.0.0/0 → Internet Gateway)
  ├── Security Group (SSH, + HTTP in Part 4)
  ├── Key Pair
  └── EC2 Instance (Ubuntu 26.04, t3.micro)
      └── user data script (nginx installation, Part 4)

Shared with the Azure version:
  ├── ../modules/ssh-key  (SSH key pair, private key saved to ssh-key.pem)
  └── ../cloud-init.sh    (nginx installation)
```

The configuration creates its own VPC instead of using the default VPC, so it mirrors the virtual network of the Azure version - and shows what a network on AWS needs for internet access.

### What You'll Learn

- How to write and understand Terraform configuration files for AWS
- Terraform workflow: init → plan → apply → destroy
- AWS VPC networking: subnet, internet gateway, route table, security group
- Automated VM provisioning with user data (cloud-init)
- SSH key-based authentication with a shared Terraform module
- Data sources: finding the newest image and the availability zones
- Comparing Terraform with CloudFormation (AWS versions of Exercise 12-13)

## Tested Environments

- AWS CloudShell (Bash)
- Ubuntu 24.04/26.04, Terraform v1.16, aws provider 6.x

## Prerequisites

Before starting, ensure you have:
- An AWS account (see [`1-cloud-account/aws`](../../1-cloud-account/aws/readme.md))
- Basic Linux command line knowledge
- Understanding of VMs and networking concepts (complete the [AWS version of Exercise 2](../../2-iaas/aws/readme.md) first)

---

## Part 1: Setup Terraform Environment

### Step 1: Open AWS CloudShell and Install Terraform

1. Open the **AWS Console** in the region you want to use
2. Click the **CloudShell** icon (>_) in the top navigation bar
3. Use **Bash** (recommended) or **PowerShell** (`pwsh`) - all commands below work the same in both

AWS CloudShell is already authenticated with your AWS account, but Terraform isn't pre-installed. **Install it into your home directory** (it stays there between CloudShell sessions):

```bash
curl -o terraform.zip https://releases.hashicorp.com/terraform/1.16.1/terraform_1.16.1_linux_amd64.zip
mkdir -p ~/bin
unzip -o terraform.zip terraform -d ~/bin
rm terraform.zip
```

**Verify Terraform installation:**

```bash
terraform version
```

You should see `Terraform v1.16.1`. If you get `command not found`, add the directory to your path: `export PATH=$HOME/bin:$PATH` (Bash) or `$env:PATH="$HOME/bin:$env:PATH"` (PowerShell).

### Step 2: Get the Terraform Files

**Download the course repository and go to the AWS directory of the exercise:**

```bash
git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
cd course-iot-cloud-computing/14-iaas-terraform/aws
```

The AWS configuration uses the shared files one directory up (`../modules/ssh-key`, `../cloud-init.sh`), so keep the directory structure of the repository.

---

## Part 2: Understand the Terraform Configuration

The AWS configuration has 5 files (see [How the Exercise is Organized](../terraform-basics.md#how-the-exercise-is-organized)). Open them with `nano <file>` or `cat <file>`, or click **Actions** → **Download file** to look at them on your computer.

### Step 3: providers.tf

```hcl
terraform {
  required_version = ">=1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>6.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "terraform-vm"
    }
  }
}
```

- `aws` - The AWS provider. It signs in with the credentials of CloudShell (or of the AWS CLI on your computer)
- `region` - comes from a variable, so you can change it without editing the file
- `default_tags` - every resource gets the tag `Project = terraform-vm`; AWS has no resource groups, so tags are the way to find related resources
- The `tls` and `local` providers come from the shared `ssh-key` module

### Step 4: variables.tf

Three input variables with default values: `region` (`eu-west-2`), `instance_type` (`t3.micro`) and `username` (`ubuntu` - only used in the `ssh_command` output, because the Ubuntu images on AWS always have the user `ubuntu`).

### Step 5: main.tf

`main.tf` uses 2 data sources and creates 8 AWS resources:

1. **Data sources** (lines 1-9): the newest Ubuntu 26.04 image, published by Canonical as a public SSM parameter, and the availability zones of the region
2. **VPC and subnet** (lines 11-30): `10.0.0.0/16` and `10.0.1.0/24` in the first availability zone; `map_public_ip_on_launch` gives the VMs in the subnet a public IP address
3. **Internet gateway, route table and association** (lines 32-58): send the traffic to the internet (`0.0.0.0/0`) through the gateway. On Azure, every virtual network has this built in
4. **Security group** (lines 60-81): allows SSH (port 22) from anywhere, and all outgoing traffic (Terraform removes the default outgoing rule of AWS, so the configuration adds it back)
5. **Key pair** (lines 83-87): registers the public key of the shared module in EC2
6. **EC2 instance** (lines 89-105): Ubuntu 26.04, `t3.micro`, in the subnet with the security group and the key pair; `http_tokens = "required"` enables only the secure version of the instance metadata service (IMDSv2)

**Key Terraform concepts:**
- References like `aws_vpc.my_terraform_network.id` create dependencies - Terraform creates the VPC first
- `aws_` prefix indicates AWS resources
- `nonsensitive(data.aws_ssm_parameter.ubuntu.value)` - SSM parameters are marked as sensitive, but an image ID isn't a secret, so the plan may show it

### Step 6: outputs.tf and ssh.tf

- `outputs.tf` returns the instance ID, the public IP address and a ready `ssh` command
- `ssh.tf` calls the shared [SSH key module](../terraform-basics.md#the-shared-ssh-key-module) with `source = "../modules/ssh-key"`

---

## Part 3: Deploy Infrastructure with Terraform

What each command does is explained in [The Terraform Workflow](../terraform-basics.md#the-terraform-workflow).

### Step 7: Initialize Terraform

```bash
terraform init -upgrade
```

**Expected output:**
```
Initializing the backend...
Initializing modules...
- ssh_key in ../modules/ssh-key
Initializing provider plugins...
- Installed hashicorp/aws v6.73.0 (signed by HashiCorp)
- Installed hashicorp/tls v4.4.2 (signed by HashiCorp)
- Installed hashicorp/local v2.9.1 (signed by HashiCorp)

Terraform has been successfully initialized!
```

### Step 8: Review the Execution Plan

```bash
terraform plan -out main.tfplan
```

If you use another region than `eu-west-2`, add it to every `plan`: `terraform plan -var region=eu-north-1 -out main.tfplan` (or change the default in `variables.tf`).

**Expected output:**
```
Terraform will perform the following actions:

  # aws_instance.my_terraform_vm will be created
  + resource "aws_instance" "my_terraform_vm" {
      + ami           = "ami-..."
      + instance_type = "t3.micro"
      ...
    }

  # ... (9 more resources)

Plan: 10 to add, 0 to change, 0 to destroy.
```

**Review the plan carefully!** Ensure the region is correct and resources match expectations.

### Step 9: Apply the Configuration

```bash
terraform apply main.tfplan
```

**Wait about 30 seconds for deployment**. You'll see progress as each resource is created.

**Expected output:**
```
aws_vpc.my_terraform_network: Creating...
aws_vpc.my_terraform_network: Creation complete after 2s [id=vpc-...]
...
aws_instance.my_terraform_vm: Creation complete after 13s [id=i-03d0a15221be062cf]

Apply complete! Resources: 10 added, 0 changed, 0 destroyed.

Outputs:

instance_id = "i-03d0a15221be062cf"
public_ip_address = "13.63.161.12"
ssh_command = "ssh -i ./ssh-key.pem ubuntu@13.63.161.12"
```

### Step 10: Verify Deployment

**Check resources in the AWS Console:**

1. Open **EC2** → **Instances**: `myVM` is `Running`
2. Open **VPC** → **Your VPCs**: `myVpc`, and its subnet, route table and internet gateway
3. Open **EC2** → **Security Groups**: `mySecurityGroup`; **EC2** → **Key Pairs**: `myKey-...`

**Or verify via AWS CLI** (`--region` must match your region):

```bash
aws ec2 describe-instances --region eu-west-2 --filters "Name=tag:Project,Values=terraform-vm" --query "Reservations[].Instances[].[InstanceId,State.Name,PublicIpAddress]" --output table
```

**Connect to the VM with SSH** (wait a minute after apply, until the VM has booted):

```bash
ssh -i ssh-key.pem ubuntu@$(terraform output -raw public_ip_address)
```

Type `yes` to trust the VM, then `exit` to leave it.

---

## Part 4: Modify Configuration to Add HTTP Access

Now you'll modify the Terraform configuration to allow HTTP traffic and install the nginx web server with the shared `cloud-init.sh` script.

### Step 11: Add HTTP Security Group Rule

**Edit main.tf** (`nano main.tf`). Find the security group (lines 60-81) and add a second `ingress` block for HTTP after the SSH rule:

```hcl
  # Add this new rule for HTTP
  ingress {
    description = "HTTP"
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }
```

### Step 12: Add the cloud-init Script to the VM

**Still editing main.tf**, find the EC2 instance (line 90) and add `user_data` after `key_name`:

```hcl
resource "aws_instance" "my_terraform_vm" {
  ...
  key_name               = aws_key_pair.my_terraform_key.key_name

  # Add these lines to install nginx on first boot (a new script needs a new VM, like on Azure)
  user_data                   = file("${path.module}/../cloud-init.sh")
  user_data_replace_on_change = true
  ...
}
```

Unlike Azure's `custom_data`, `user_data` is plain text - the provider encodes it. Without `user_data_replace_on_change`, Terraform would stop the instance, change the script and start it again - but cloud-init runs the script only on the first boot, so nginx wouldn't be installed. See [The Shared nginx Script](../terraform-basics.md#the-shared-nginx-script) for what `cloud-init.sh` does.

**Save** the file (`Ctrl+X`, `Y`, `Enter` in nano) and check the syntax:

```bash
terraform fmt
terraform validate
```

### Step 13: Apply the Changes

```bash
terraform plan -out main.tfplan
```

**Expected output:**
```
  # aws_instance.my_terraform_vm must be replaced
-/+ resource "aws_instance" "my_terraform_vm" {
      + user_data                   = "..." # forces replacement
      ...

  # aws_security_group.my_terraform_sg will be updated in-place
  ~ resource "aws_security_group" "my_terraform_sg" {
      ~ ingress = [
          + {
              + description = "HTTP"
              ...

Plan: 1 to add, 1 to change, 1 to destroy.
```

**Important:** The VM will be **replaced** (destroyed and recreated), and it gets a new public IP address.

```bash
terraform apply main.tfplan
```

Wait about 1 minute for the VM to be recreated, and 1-2 more minutes for nginx to install.

### Step 14: Test the Web Server

```bash
curl http://$(terraform output -raw public_ip_address)
```

**Expected output:**
```html
<h1>Hello World from ip-10-0-1-115</h1>
```

(`hostname -f` prints the internal name of the instance, made from its private IP address.) Or open `http://<your-public-ip-address>` in your browser.

---

## Part 5: Understanding Terraform State

### Step 15: Explore Terraform State

Run `terraform state list` and `terraform show` - see [Terraform State](../terraform-basics.md#terraform-state).

**Expected output of `terraform state list`:**
```
data.aws_availability_zones.available
data.aws_ssm_parameter.ubuntu
aws_instance.my_terraform_vm
aws_internet_gateway.my_terraform_gateway
aws_key_pair.my_terraform_key
aws_route_table.my_terraform_route_table
aws_route_table_association.my_terraform_route_table_association
aws_security_group.my_terraform_sg
aws_subnet.my_terraform_subnet
aws_vpc.my_terraform_network
module.ssh_key.local_sensitive_file.private_key
module.ssh_key.tls_private_key.ssh
```

The data sources are in the state too, but Terraform only reads them - it never creates or deletes them.

---

## Cleanup

**Important:** Delete all resources to avoid charges once the Free Tier ends!

### Step 16: Destroy Infrastructure

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```

(Add `-var region=<region>` to the `plan` if you used another region.) Wait about 30 seconds. All 10 resources are deleted, including `ssh-key.pem`.

**Verify cleanup** - nothing should be listed:

```bash
aws ec2 describe-vpcs --region eu-west-2 --filters "Name=tag:Project,Values=terraform-vm" --query "Vpcs[].VpcId" --output text
```

---

## Troubleshooting

The common Terraform problems (init, references, state, web server, SSH) are in [Common Troubleshooting](../terraform-basics.md#common-troubleshooting). AWS-specific ones:

### Plan fails with "No valid credential sources found"

- **Run Terraform in CloudShell**, or configure the AWS CLI on your computer (`aws configure` or `aws login`) and check `aws sts get-caller-identity`

### Apply fails with "Unsupported" or "not eligible for Free Tier" for t3.micro

- **Use t2.micro**: `terraform plan -var instance_type=t2.micro -out main.tfplan` (some regions offer t2.micro in the Free Tier)

### Apply fails with "UnauthorizedOperation" or "not authorized" in another region

- **Your account may be limited to one region**: Use the region of your account with `-var region=<region>`

### Apply fails with "VpcLimitExceeded"

- **A region allows 5 VPCs**: Delete VPCs you don't need (VPC console), or destroy older Terraform deployments

### Plan shows changes to the AMI after some time

- **Canonical published a newer image**: The data source always reads the newest one; applying would replace the VM. Run `terraform plan` to see it before `apply`

---

## Summary and Learning Outcomes

Congratulations! You've deployed AWS infrastructure using Terraform. You learned:

✅ **Terraform Fundamentals**: HCL syntax, providers, resources, data sources, variables, outputs, modules
✅ **Terraform Workflow**: init → plan → apply → destroy lifecycle
✅ **AWS VM Infrastructure**: VPC, subnet, internet gateway, route table, security group, EC2
✅ **Security Groups**: Opening specific ports (SSH, HTTP)
✅ **Cloud-Init**: Automated VM configuration on first boot
✅ **SSH Key Management**: Keys generated by a module shared with the Azure version
✅ **State Management**: Understanding terraform.tfstate
✅ **IaC Benefits**: Repeatable, version-controlled infrastructure

### Terraform vs CloudFormation

**Terraform Advantages:**
- Multi-cloud support - compare with the [Azure version](../readme.md): same workflow, same module and script, different resources
- `terraform plan` shows changes to resources created outside the configuration too
- Code can be shared between clouds (modules)

**CloudFormation Advantages:**
- No state file to manage - the stack is the state
- Automatic rollback when a deployment fails
- No tool to install in CloudShell

## Optional Next Steps

- Compare this exercise with the AWS version of Exercise 2 (manual EC2 creation) - how much faster is IaC?
- Deploy the [Azure version](../readme.md) with the same module and script
- Modify the configuration to use a different instance type or an ARM (Graviton) image (`t4g.micro` + the `arm64` SSM parameter)
- Add a second subnet in another availability zone and a second VM
- Store Terraform state remotely in an S3 bucket (`backend "s3"`)
- Compare with Exercise 15 (IoT with Terraform) to see Terraform for different services
- Use `terraform import` to bring the default VPC under Terraform management
