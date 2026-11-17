# Azure Virtual Machine with Terraform

> Using AWS instead? Follow the [AWS version of this exercise](aws/readme.md).

In this exercise, you'll learn **Terraform** - a popular multi-cloud Infrastructure as Code (IaC) tool. You'll deploy a complete Linux VM infrastructure on Azure, including networking, security, and automated web server installation.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

**Read first:** [Terraform Basics](terraform-basics.md) - what Terraform is, how this exercise is organized, the workflow and the state. That page is shared with the AWS version; this readme contains only the Azure steps.

## Architecture Overview

This Terraform configuration deploys a complete VM infrastructure:

```
Resource Group (rg-<random-name>)
  ├── Virtual Network (10.0.0.0/16)
  │   └── Subnet (10.0.1.0/24)
  ├── Public IP Address
  ├── Network Security Group (SSH, + HTTP in Part 4)
  ├── Network Interface
  └── Linux Virtual Machine (Ubuntu 26.04, Standard_B1s)
      └── cloud-init script (nginx installation, Part 4)

Shared with the AWS version:
  ├── modules/ssh-key  (SSH key pair, private key saved to ssh-key.pem)
  └── cloud-init.sh    (nginx installation)
```

### What You'll Learn

- How to write and understand Terraform configuration files
- Terraform workflow: init → plan → apply → destroy
- Azure VM infrastructure components and dependencies
- Network security group configuration
- Automated VM provisioning with cloud-init
- SSH key-based authentication with a shared Terraform module
- Terraform state management
- Comparing Terraform with Bicep (Exercise 12-13)

## Tested Environments

- Azure Cloud Shell (Bash)
- Ubuntu 24.04/26.04, Terraform v1.16, azurerm provider 4.x

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- Basic Linux command line knowledge
- Understanding of VMs and networking concepts (complete Exercise 2 first)

The `Standard_B1s` size is in the Azure free services (750 hours per month for 12 months) and in the Azure for Students offer; the public IP address and the disk cost a few cents per day. Destroy everything at the end of the exercise.

---

## Part 1: Setup Terraform Environment

### Step 1: Open Azure Cloud Shell

1. Navigate to the **Azure Portal** (portal.azure.com)
2. Click the **Cloud Shell** icon (>_) in the top navigation bar
3. Use **Bash** (recommended) or **PowerShell** - all commands below work the same in both

**Why Cloud Shell?** It has Terraform pre-installed and is already authenticated with your Azure subscription.

**Verify Terraform installation:**

```bash
terraform version
```

You should see output like: `Terraform v1.16.1` or similar.

### Step 2: Get the Terraform Files

**Download the course repository and go to the exercise directory:**

```bash
git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
cd course-iot-cloud-computing/14-iaas-terraform
```

---

## Part 2: Understand the Terraform Configuration

The Azure configuration has 5 files (see [How the Exercise is Organized](terraform-basics.md#how-the-exercise-is-organized)). Open them with `code <file>` (the Cloud Shell editor) or `cat <file>`.

### Step 3: providers.tf

```hcl
terraform {
  required_version = ">=1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}
```

- `azurerm` - Main Azure provider for resources. It signs in with your Azure CLI login and uses the active subscription (`az account show`)
- `random` - Generates random values for unique names
- The `tls` and `local` providers come from the shared `ssh-key` module

### Step 4: variables.tf

Three input variables with default values: `resource_group_location` (`uksouth`), `resource_group_name_prefix` (`rg`) and `username` (`azureadmin`). Change the location here, or pass `-var resource_group_location=<region>` to `terraform plan`.

### Step 5: main.tf

`main.tf` creates 8 Azure resources:

1. **random_pet + resource group** (lines 1-8): a resource group with a random name like `rg-adapting-redfish`
2. **Virtual network and subnet** (lines 10-24): `10.0.0.0/16` and `10.0.1.0/24`
3. **Public IP** (lines 26-33): a static Standard IP address
4. **Network security group** (lines 35-52): allows SSH (port 22) from anywhere
5. **Network interface + association** (lines 54-72): connects the VM to the subnet, the public IP and the security group
6. **Virtual machine** (lines 74-105): Ubuntu 26.04, `Standard_B1s`, the SSH key from the module, boot diagnostics

**Key Terraform concepts:**
- References like `azurerm_resource_group.rg.name` create dependencies - Terraform creates the resource group first
- `azurerm_` prefix indicates Azure resources
- `public_key = module.ssh_key.public_key_openssh` uses the output of the shared module

### Step 6: outputs.tf and ssh.tf

- `outputs.tf` returns the resource group name, the public IP address and a ready `ssh` command
- `ssh.tf` calls the shared [SSH key module](terraform-basics.md#the-shared-ssh-key-module)

---

## Part 3: Deploy Infrastructure with Terraform

What each command does is explained in [The Terraform Workflow](terraform-basics.md#the-terraform-workflow).

### Step 7: Initialize Terraform

```bash
terraform init -upgrade
```

**Expected output:**
```
Initializing the backend...
Initializing modules...
- ssh_key in modules/ssh-key
Initializing provider plugins...
- Installed hashicorp/azurerm v4.81.0 (signed by HashiCorp)
- Installed hashicorp/random v3.9.1 (signed by HashiCorp)
- Installed hashicorp/tls v4.4.2 (signed by HashiCorp)
- Installed hashicorp/local v2.9.1 (signed by HashiCorp)

Terraform has been successfully initialized!
```

### Step 8: Review the Execution Plan

```bash
terraform plan -out main.tfplan
```

**Expected output:**
```
Terraform will perform the following actions:

  # azurerm_linux_virtual_machine.my_terraform_vm will be created
  + resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
      + name                  = "myVM"
      + size                  = "Standard_B1s"
      ...
    }

  # ... (10 more resources)

Plan: 11 to add, 0 to change, 0 to destroy.
```

**Review the plan carefully!** Ensure the region is correct and resources match expectations.

### Step 9: Apply the Configuration

```bash
terraform apply main.tfplan
```

**Wait about 2 minutes for deployment**. You'll see progress as each resource is created.

**Expected output:**
```
azurerm_resource_group.rg: Creating...
azurerm_resource_group.rg: Creation complete after 2s
...
azurerm_linux_virtual_machine.my_terraform_vm: Creation complete after 51s

Apply complete! Resources: 11 added, 0 changed, 0 destroyed.

Outputs:

public_ip_address = "20.26.220.60"
resource_group_name = "rg-adapting-redfish"
ssh_command = "ssh -i ./ssh-key.pem azureadmin@20.26.220.60"
```

### Step 10: Verify Deployment

**Check resources in Azure Portal:**

1. Navigate to Azure Portal
2. Find your resource group (e.g., `rg-adapting-redfish`)
3. Verify all resources exist: Virtual Machine (myVM), Virtual Network (myVnet), Network Security Group (myNetworkSecurityGroup), Public IP (myPublicIP), Network Interface (myNIC), Disk (myOsDisk)

**Or verify via Azure CLI:**

```bash
az vm list --resource-group $(terraform output -raw resource_group_name) --output table
```

**Connect to the VM with SSH** (wait a minute after apply, until the VM has booted):

```bash
ssh -i ssh-key.pem azureadmin@$(terraform output -raw public_ip_address)
```

Type `yes` to trust the VM, then `exit` to leave it.

---

## Part 4: Modify Configuration to Add HTTP Access

Now you'll modify the Terraform configuration to allow HTTP traffic and install the nginx web server with the shared `cloud-init.sh` script.

### Step 11: Add HTTP Security Rule

**Edit main.tf** (`code main.tf`). Find the Network Security Group (lines 35-52) and add a second `security_rule` block for HTTP after the SSH rule:

```hcl
  # Add this new security rule for HTTP
  security_rule {
    name                       = "HTTP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
```

### Step 12: Add the cloud-init Script to the VM

**Still editing main.tf**, find the VM resource (line 75) and add `custom_data` after `size`:

```hcl
resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
  ...
  size                  = "Standard_B1s"

  # Add this line to install nginx on first boot
  custom_data = base64encode(file("${path.module}/cloud-init.sh"))
  ...
}
```

Azure expects `custom_data` base64-encoded. See [The Shared nginx Script](terraform-basics.md#the-shared-nginx-script) for what `cloud-init.sh` does.

**Save** the file (`Ctrl+S` in the editor) and check the syntax:

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
  # azurerm_linux_virtual_machine.my_terraform_vm must be replaced
-/+ resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
      + custom_data = (sensitive value) # forces replacement
      ...

  # azurerm_network_security_group.my_terraform_nsg will be updated in-place
  ~ resource "azurerm_network_security_group" "my_terraform_nsg" {
      ~ security_rule = [
          + {
              + name = "HTTP"
              ...

Plan: 1 to add, 1 to change, 1 to destroy.
```

**Important:** The VM will be **replaced** (destroyed and recreated) because `custom_data` can't be changed on existing VMs.

```bash
terraform apply main.tfplan
```

Wait about 2 minutes for the VM to be recreated, and 1-2 more minutes for nginx to install.

### Step 14: Test the Web Server

```bash
curl http://$(terraform output -raw public_ip_address)
```

**Expected output:**
```html
<h1>Hello World from hostname-terraform.0p1rrqeqomlupo2qawv2fbo5kg.zx.internal.cloudapp.net</h1>
```

(`hostname -f` prints the full internal DNS name of the VM.) Or open `http://<your-public-ip-address>` in your browser.

---

## Part 5: Understanding Terraform State

### Step 15: Explore Terraform State

Run `terraform state list` and `terraform show` - see [Terraform State](terraform-basics.md#terraform-state).

**Expected output of `terraform state list`:**
```
azurerm_linux_virtual_machine.my_terraform_vm
azurerm_network_interface.my_terraform_nic
azurerm_network_interface_security_group_association.example
azurerm_network_security_group.my_terraform_nsg
azurerm_public_ip.my_terraform_public_ip
azurerm_resource_group.rg
azurerm_subnet.my_terraform_subnet
azurerm_virtual_network.my_terraform_network
random_pet.rg_name
module.ssh_key.local_sensitive_file.private_key
module.ssh_key.tls_private_key.ssh
```

---

## Cleanup

**Important:** Delete all resources to avoid ongoing charges!

### Step 16: Destroy Infrastructure

```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```

Wait about 2 minutes. All 11 resources are deleted, including the resource group and `ssh-key.pem`.

**Verify cleanup:**

```bash
az group list --query "[?starts_with(name, 'rg-')].name" --output table
```

Your resource group should be gone.

---

## Troubleshooting

The common Terraform problems (init, references, state, web server, SSH) are in [Common Troubleshooting](terraform-basics.md#common-troubleshooting). Azure-specific ones:

### Plan or apply fails with "subscription ID could not be determined"

- **Sign in**: Run `az login` (not needed in Cloud Shell) and check `az account show`
- **Pick the subscription**: Run `az account set --subscription <id>`, or `export ARM_SUBSCRIPTION_ID=<id>` (Bash) / `$env:ARM_SUBSCRIPTION_ID="<id>"` (PowerShell)

### Apply fails with "SkuNotAvailable" or a quota error for the VM

- **Check the size in your region**: `az vm list-skus --location uksouth --size Standard_B1s --output table`
- **Use another allowed region**: `terraform plan -var resource_group_location=<region> -out main.tfplan`

### Apply fails with "RequestDisallowedByPolicy"

- **Your subscription doesn't allow the region**: Check the Policy assignments (see the note at the top) and use an allowed region

---

## Summary and Learning Outcomes

Congratulations! You've deployed infrastructure using Terraform. You learned:

✅ **Terraform Fundamentals**: HCL syntax, providers, resources, variables, outputs, modules
✅ **Terraform Workflow**: init → plan → apply → destroy lifecycle
✅ **Azure VM Infrastructure**: Networking, security, compute
✅ **Security Groups**: Opening specific ports (SSH, HTTP)
✅ **Cloud-Init**: Automated VM configuration on first boot
✅ **SSH Key Management**: Keys generated by a shared module
✅ **State Management**: Understanding terraform.tfstate
✅ **IaC Benefits**: Repeatable, version-controlled infrastructure

### Terraform vs Bicep Comparison (Exercise 12 Revisited)

**Terraform Advantages:**
- Multi-cloud support (AWS, GCP, Azure, etc.) - compare with the [AWS version](aws/readme.md): same workflow, same module and script, different resources
- Larger ecosystem and community
- More providers (1000+)
- `terraform plan` shows changes to resources created outside the configuration too

**Bicep Advantages:**
- Simpler for Azure-only workloads
- Better Azure Portal integration
- No state file to manage
- New Azure features available on day one

**When to use each:**
- **Terraform**: Multi-cloud, complex workflows, existing Terraform codebase
- **Bicep**: Azure-only, simpler projects, tight Azure integration

## Optional Next Steps

- Compare this exercise with Exercise 2 (manual VM creation) - how much faster is IaC?
- Deploy the [AWS version](aws/readme.md) with the same module and script
- Modify the configuration to use a different VM size or Linux distribution
- Add a second VM to create a VM cluster
- Store Terraform state remotely in an Azure Storage Account (`backend "azurerm"`)
- Explore Terraform workspaces for managing multiple environments (dev/staging/prod)
- Compare with Exercise 15 (IoT Hub with Terraform) to see Terraform for different services
- Add data sources to query existing Azure resources
- Use `terraform import` to bring existing resources under Terraform management
