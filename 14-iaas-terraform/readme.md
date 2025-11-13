# Azure Virtual Machine with Terraform

In this exercise, you'll learn **Terraform** - a popular multi-cloud Infrastructure as Code (IaC) tool. You'll deploy a complete Linux VM infrastructure on Azure, including networking, security, and automated web server installation.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## What is Terraform?

**Terraform** is an open-source Infrastructure as Code tool created by HashiCorp. It's:
- **Cloud-agnostic** - Works with AWS, Azure, GCP, and 100+ other providers
- **Declarative** - Describe what you want, Terraform figures out how to create it
- **State-managed** - Tracks infrastructure state to detect and manage changes
- **Widely adopted** - Industry standard for multi-cloud IaC

### Terraform vs Bicep

| Feature | Terraform | Bicep |
|---------|-----------|-------|
| Cloud Support | Multi-cloud (AWS, Azure, GCP, etc.) | Azure only |
| Language | HCL (HashiCorp Configuration Language) | Bicep DSL |
| State Management | Requires state file | Managed by Azure |
| Maturity | Since 2014 (mature ecosystem) | Since 2021 (newer) |
| Provider Ecosystem | 1000+ providers | Azure services only |
| Learning Curve | Moderate | Easy (if Azure-focused) |

Use **Bicep** if: You only work with Azure and want tight integration
Use **Terraform** if: You work with multiple clouds or need provider flexibility

## Architecture Overview

This Terraform configuration deploys a complete VM infrastructure:

```
Resource Group
  ├── Virtual Network (10.0.0.0/16)
  │   └── Subnet (10.0.1.0/24)
  ├── Public IP Address
  ├── Network Security Group (SSH + HTTP rules)
  ├── Network Interface
  ├── Storage Account (boot diagnostics)
  ├── SSH Key Pair (auto-generated)
  └── Linux Virtual Machine (Ubuntu 22.04)
      └── Custom Script Extension (nginx installation)
```

### What You'll Learn

- How to write and understand Terraform configuration files
- Terraform workflow: init → plan → apply → destroy
- Azure VM infrastructure components and dependencies
- Network security group configuration
- Automated VM provisioning with custom scripts
- SSH key-based authentication
- Terraform state management
- Comparing Terraform with Bicep (Exercise 12-13)

## Tested Environments

- Ubuntu 22.04
- Terraform v1.11.0
- Azure Cloud Shell (Bash)

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- Basic Linux command line knowledge
- Understanding of VMs and networking concepts (complete Exercise 2 first)

---

## Part 1: Setup Terraform Environment

### Step 1: Open Azure Cloud Shell

1. Navigate to the **Azure Portal** (portal.azure.com)
2. Click the **Cloud Shell** icon (>_) in the top navigation bar
3. Ensure you're using the **Bash** environment (not PowerShell)

**Why Cloud Shell?** It has Terraform pre-installed and is already authenticated with your Azure subscription.

**Verify Terraform installation:**

```bash
terraform version
```

You should see output like: `Terraform v1.11.0` or similar.

### Step 2: Create Terraform Project Directory

**Create and navigate to project directory:**

```bash
mkdir terraform-vm
cd terraform-vm
```

---

## Part 2: Create Terraform Configuration Files

Terraform uses multiple `.tf` files to organize configuration. You'll create 5 files:

1. **providers.tf** - Configure Terraform and Azure provider
2. **variables.tf** - Define input variables
3. **main.tf** - Define resources to create
4. **outputs.tf** - Define values to output after deployment
5. **ssh.tf** - Generate SSH keys automatically

### Step 3: Create providers.tf

**Create the file:**

```bash
nano providers.tf
```

**Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code providers.tf` to open the Cloud Shell editor (GUI).

**Copy and paste this content:**

```hcl
terraform {
  required_version = ">=0.12"

  required_providers {
    azapi = {
      source  = "azure/azapi"
      version = "~>1.5"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
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

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

**What this does:**
- Specifies minimum Terraform version (0.12+)
- Declares three providers:
  - `azurerm` - Main Azure provider for resources
  - `azapi` - Azure API provider for advanced resources
  - `random` - Generates random values for unique names
- Configures the Azure provider

### Step 4: Create variables.tf

**Create the file:**

```bash
nano variables.tf
```

**Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code variables.tf` to open the Cloud Shell editor (GUI).

**Copy and paste this content:**

```hcl
variable "resource_group_location" {
  type        = string
  default     = "uksouth"
  description = "Location of the resource group."
}

variable "resource_group_name_prefix" {
  type        = string
  default     = "rg"
  description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
}

variable "username" {
  type        = string
  description = "The username for the local account that will be created on the new VM."
  default     = "azureadmin"
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Defines three input variables with default values
- Variables make Terraform configuration reusable
- You can override defaults when running `terraform apply`

### Step 5: Create main.tf

**Create the file:**

```bash
nano main.tf
```

**Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code main.tf` to open the Cloud Shell editor (GUI).

**Copy and paste this content:**

```hcl
resource "random_pet" "rg_name" {
  prefix = var.resource_group_name_prefix
}

resource "azurerm_resource_group" "rg" {
  location = var.resource_group_location
  name     = random_pet.rg_name.id
}

# Create virtual network
resource "azurerm_virtual_network" "my_terraform_network" {
  name                = "myVnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# Create subnet
resource "azurerm_subnet" "my_terraform_subnet" {
  name                 = "mySubnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.my_terraform_network.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Create public IPs
resource "azurerm_public_ip" "my_terraform_public_ip" {
  name                = "myPublicIP"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Dynamic"
}

# Create Network Security Group and rule
resource "azurerm_network_security_group" "my_terraform_nsg" {
  name                = "myNetworkSecurityGroup"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Create network interface
resource "azurerm_network_interface" "my_terraform_nic" {
  name                = "myNIC"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "my_nic_configuration"
    subnet_id                     = azurerm_subnet.my_terraform_subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.my_terraform_public_ip.id
  }
}

# Connect the security group to the network interface
resource "azurerm_network_interface_security_group_association" "example" {
  network_interface_id      = azurerm_network_interface.my_terraform_nic.id
  network_security_group_id = azurerm_network_security_group.my_terraform_nsg.id
}

# Generate random text for a unique storage account name
resource "random_id" "random_id" {
  keepers = {
    # Generate a new ID only when a new resource group is defined
    resource_group = azurerm_resource_group.rg.name
  }

  byte_length = 8
}

# Create storage account for boot diagnostics
resource "azurerm_storage_account" "my_storage_account" {
  name                     = "diag${random_id.random_id.hex}"
  location                 = azurerm_resource_group.rg.location
  resource_group_name      = azurerm_resource_group.rg.name
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Create virtual machine
resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
  name                  = "myVM"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  network_interface_ids = [azurerm_network_interface.my_terraform_nic.id]
  size                  = "Standard_B1s"

  os_disk {
    name                 = "myOsDisk"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  computer_name  = "hostname-terraform"
  admin_username = var.username

  admin_ssh_key {
    username   = var.username
    public_key = azapi_resource_action.ssh_public_key_gen.output.publicKey
  }

  boot_diagnostics {
    storage_account_uri = azurerm_storage_account.my_storage_account.primary_blob_endpoint
  }
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Creates 10 Azure resources in a specific order
- Uses `random_pet` to generate unique resource group name
- Defines networking (VNet, subnet, public IP, NSG)
- Creates VM with Ubuntu 22.04 LTS
- Configures SSH key authentication
- Sets up boot diagnostics for troubleshooting

**Key Terraform concepts:**
- `resource` blocks define what to create
- `azurerm_` prefix indicates Azure resources
- References like `azurerm_resource_group.rg.name` create dependencies
- Terraform automatically determines creation order

### Step 6: Create outputs.tf

**Create the file:**

```bash
nano outputs.tf
```

**Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code outputs.tf` to open the Cloud Shell editor (GUI).

**Copy and paste this content:**

```hcl
output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "public_ip_address" {
  value = azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Defines outputs displayed after `terraform apply`
- Outputs are useful for getting IPs, names, connection strings
- You can reference outputs in other Terraform modules

### Step 7: Create ssh.tf

**Create the file:**

```bash
nano ssh.tf
```

**Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code ssh.tf` to open the Cloud Shell editor (GUI).

**Copy and paste this content:**

```hcl
resource "random_pet" "ssh_key_name" {
  prefix    = "ssh"
  separator = ""
}

resource "azapi_resource_action" "ssh_public_key_gen" {
  type        = "Microsoft.Compute/sshPublicKeys@2022-11-01"
  resource_id = azapi_resource.ssh_public_key.id
  action      = "generateKeyPair"
  method      = "POST"

  response_export_values = ["publicKey", "privateKey"]
}

resource "azapi_resource" "ssh_public_key" {
  type      = "Microsoft.Compute/sshPublicKeys@2022-11-01"
  name      = random_pet.ssh_key_name.id
  location  = azurerm_resource_group.rg.location
  parent_id = azurerm_resource_group.rg.id
}

output "key_data" {
  value = azapi_resource_action.ssh_public_key_gen.output.publicKey
}
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**What this does:**
- Automatically generates SSH key pair in Azure
- No need to manually create or manage SSH keys
- Public key is used by the VM (in main.tf)
- Private key can be retrieved if needed for SSH access

---

## Part 3: Deploy Infrastructure with Terraform

### Step 8: Initialize Terraform

**Run terraform init:**

```bash
terraform init -upgrade
```

**What this does:**
- Downloads required provider plugins (azurerm, azapi, random)
- Initializes the backend (where state is stored)
- Validates configuration syntax
- Creates `.terraform` directory and lock file

**Expected output:**
```
Initializing the backend...
Initializing provider plugins...
- Finding azure/azapi versions matching "~> 1.5"...
- Finding hashicorp/azurerm versions matching "~> 3.0"...
- Finding hashicorp/random versions matching "~> 3.0"...

Terraform has been successfully initialized!
```

### Step 9: Review the Execution Plan

**Create an execution plan:**

```bash
terraform plan -out main.tfplan
```

**What this does:**
- Analyzes configuration files
- Compares desired state with current state
- Shows what will be created, modified, or destroyed
- Saves plan to `main.tfplan` file

**Expected output:**
```
Terraform will perform the following actions:

  # azurerm_linux_virtual_machine.my_terraform_vm will be created
  + resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
      + name                  = "myVM"
      + size                  = "Standard_B1s"
      ...
    }

  # ... (10-12 more resources)

Plan: 12 to add, 0 to change, 0 to destroy.
```

**Review the plan carefully!** Ensure the region is correct and resources match expectations.

### Step 10: Apply the Configuration

**Deploy the infrastructure:**

```bash
terraform apply main.tfplan
```

**Wait 3-5 minutes for deployment**. You'll see progress as each resource is created.

**Expected output:**
```
azurerm_resource_group.rg: Creating...
azurerm_resource_group.rg: Creation complete after 2s
azurerm_virtual_network.my_terraform_network: Creating...
...
azurerm_linux_virtual_machine.my_terraform_vm: Still creating... [1m30s elapsed]
azurerm_linux_virtual_machine.my_terraform_vm: Creation complete after 2m15s

Apply complete! Resources: 12 added, 0 changed, 0 destroyed.

Outputs:

public_ip_address = "20.123.45.67"
resource_group_name = "rg-keen-tortoise"
```

**Important:** Save the **public_ip_address** - you'll need it later!

### Step 11: Verify Deployment

**Check resources in Azure Portal:**

1. Navigate to Azure Portal
2. Find your resource group (e.g., `rg-keen-tortoise`)
3. Verify all resources exist:
   - Virtual Machine (myVM)
   - Virtual Network (myVnet)
   - Network Security Group (myNetworkSecurityGroup)
   - Public IP (myPublicIP)
   - Storage Account (diag...)

**Or verify via Azure CLI:**

**Using Bash:**
```bash
az vm list --resource-group $(terraform output -raw resource_group_name) --output table
```

**Using PowerShell:**
```powershell
az vm list --resource-group $(terraform output -raw resource_group_name) --output table
```

---

## Part 4: Modify Configuration to Add HTTP Access

Now you'll modify the Terraform configuration to allow HTTP traffic and install nginx web server.

### Step 12: Add HTTP Security Rule

**Edit main.tf:**

```bash
nano main.tf
```

**Find the Network Security Group section** (around line 35-50) and add a second `security_rule` block for HTTP:

```hcl
# Create Network Security Group and rule
resource "azurerm_network_security_group" "my_terraform_nsg" {
  name                = "myNetworkSecurityGroup"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

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
}
```

**Save**: `Ctrl+X`, `Y`, `Enter`

### Step 13: Add Custom Script to Install Nginx

**Still editing main.tf**, find the VM resource (around line 92-124) and add `custom_data` field:

```hcl
resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
  name                  = "myVM"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  network_interface_ids = [azurerm_network_interface.my_terraform_nic.id]
  size                  = "Standard_B1s"

  # Add this line to install nginx on first boot
  custom_data = base64encode(file("${path.module}/cloud-init.txt"))

  os_disk {
    name                 = "myOsDisk"
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  # ... rest of configuration
}
```

**Save**: `Ctrl+X`, `Y`, `Enter`

### Step 14: Create Cloud-Init Script

**Create cloud-init.txt file:**

```bash
nano cloud-init.txt
```

**Note:** In Azure Cloud Shell, `nano` works in both Bash and PowerShell modes. Alternatively, you can use `code cloud-init.txt` to open the Cloud Shell editor (GUI).

**Copy and paste this content:**

```bash
#!/bin/bash
# Install and configure nginx web server
sudo apt update -y
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
echo "<h1>Hello World from $(hostname -f)</h1>" | sudo tee /var/www/html/index.html
```

**Save**: `Ctrl+X`, `Y`, `Enter`

**What this script does:**
1. Updates package lists
2. Installs nginx web server
3. Starts and enables nginx service
4. Creates a custom welcome page with hostname

### Step 15: Apply the Changes

**Create a new plan:**

```bash
terraform plan -out main.tfplan
```

**Expected output:**
```
Terraform will perform the following actions:

  # azurerm_linux_virtual_machine.my_terraform_vm must be replaced
-/+ resource "azurerm_linux_virtual_machine" "my_terraform_vm" {
      ~ custom_data = (known after apply)
      # ... VM will be recreated with new custom_data

  # azurerm_network_security_group.my_terraform_nsg will be updated in-place
  ~ resource "azurerm_network_security_group" "my_terraform_nsg" {
      + security_rule {
          + name = "HTTP"
          ...
        }
    }

Plan: 1 to add, 1 to change, 1 to destroy.
```

**Important:** The VM will be **replaced** (destroyed and recreated) because `custom_data` can't be changed on existing VMs.

**Apply the changes:**

```bash
terraform apply main.tfplan
```

Wait 3-5 minutes for the VM to be recreated and nginx to install.

### Step 16: Test the Web Server

**Get the public IP address:**

```bash
terraform output public_ip_address
```

**Option 1: Test with curl (in Cloud Shell):**

```bash
curl http://$(terraform output -raw public_ip_address)
```

**Expected output:**
```html
<h1>Hello World from hostname-terraform</h1>
```

**Option 2: Test in web browser:**

Open your browser and navigate to:
```
http://<your-public-ip-address>
```

You should see the welcome page!

---

## Part 5: Understanding Terraform State

### Step 17: Explore Terraform State

**View current state:**

```bash
terraform show
```

This displays all managed resources and their current attributes.

**List resources in state:**

```bash
terraform state list
```

**Expected output:**
```
azapi_resource.ssh_public_key
azapi_resource_action.ssh_public_key_gen
azurerm_linux_virtual_machine.my_terraform_vm
azurerm_network_interface.my_terraform_nic
azurerm_network_interface_security_group_association.example
azurerm_network_security_group.my_terraform_nsg
azurerm_public_ip.my_terraform_public_ip
azurerm_resource_group.rg
azurerm_storage_account.my_storage_account
azurerm_subnet.my_terraform_subnet
azurerm_virtual_network.my_terraform_network
random_id.random_id
random_pet.rg_name
random_pet.ssh_key_name
```

**What is Terraform state?**
- Tracks mapping between configuration and real resources
- Stored in `terraform.tfstate` file
- Contains resource IDs, attributes, metadata
- **Important:** Never manually edit state file!
- In production, store state remotely (Azure Storage, Terraform Cloud)

---

## Cleanup

**Important:** Delete all resources to avoid ongoing charges!

### Step 18: Destroy Infrastructure

**Create destroy plan:**

```bash
terraform plan -destroy -out main.destroy.tfplan
```

**Review the plan** - it shows what will be destroyed.

**Apply the destroy plan:**

```bash
terraform apply main.destroy.tfplan
```

Wait 2-3 minutes. All resources will be deleted.

**Verify cleanup:**

**Using Bash:**
```bash
az group list --output table | grep rg-
```

**Using PowerShell:**
```powershell
az group list --output table | grep rg-
```

The resource group should be gone.

---

## Troubleshooting

### Terraform init fails with "could not query provider registry"

- **Check internet connection**: Cloud Shell needs internet access
- **Clear cache**: Delete `.terraform` directory and run `terraform init` again
- **Update Terraform**: Run `terraform version` to check version

### Plan shows "Error: Reference to undeclared resource"

- **Check resource names**: Ensure all references match resource names exactly
- **Check file syntax**: Run `terraform validate` to check syntax
- **Check dependencies**: Some resources need others to exist first

### Apply fails with "A resource with the ID already exists"

- **Check state file**: You might have state conflicts
- **Import existing resource**: Use `terraform import` if resource exists
- **Delete and recreate**: Remove from state with `terraform state rm`

### VM deployment takes too long or times out

- **Check Azure region**: Some regions are slower than others
- **Check quota**: You may have reached VM quota limit
- **Retry**: Sometimes Azure has temporary issues, try again

### Cannot access web server after deployment

- **Wait 2-3 minutes**: Cloud-init script takes time to run
- **Check public IP**: Use `terraform output public_ip_address`
- **Check NSG rules**: Verify port 80 is open in Azure Portal
- **Check nginx status**: SSH to VM and run `sudo systemctl status nginx`

### "InvalidParameter" error for custom_data

- **Check file exists**: Ensure `cloud-init.txt` is in the same directory
- **Check base64encode**: Syntax must be `base64encode(file("${path.module}/cloud-init.txt"))`
- **Check script format**: Ensure cloud-init.txt has Unix line endings (LF not CRLF)

---

## Summary and Learning Outcomes

Congratulations! You've deployed infrastructure using Terraform. You learned:

✅ **Terraform Fundamentals**: HCL syntax, providers, resources, variables, outputs
✅ **Terraform Workflow**: init → plan → apply → destroy lifecycle
✅ **Azure VM Infrastructure**: Networking, security, storage, compute
✅ **Security Groups**: Opening specific ports (SSH, HTTP)
✅ **Cloud-Init**: Automated VM configuration on first boot
✅ **SSH Key Management**: Auto-generated keys with azapi provider
✅ **State Management**: Understanding terraform.tfstate
✅ **IaC Benefits**: Repeatable, version-controlled infrastructure

### Terraform Key Concepts

**Resources**: Building blocks of infrastructure
```hcl
resource "azurerm_virtual_machine" "example" {
  name = "myVM"
  ...
}
```

**Variables**: Parameterize configuration
```hcl
variable "location" {
  default = "uksouth"
}
```

**Outputs**: Return values from deployment
```hcl
output "ip" {
  value = azurerm_public_ip.example.ip_address
}
```

**Dependencies**: Terraform automatically handles order
- Implicit: References create dependencies
- Explicit: Use `depends_on` when needed

### Terraform vs Bicep Comparison (Exercise 12 Revisited)

**Terraform Advantages:**
- Multi-cloud support (AWS, GCP, Azure, etc.)
- Larger ecosystem and community
- More providers (1000+)
- More mature (10+ years)

**Bicep Advantages:**
- Simpler for Azure-only workloads
- Better Azure Portal integration
- No state file to manage
- Faster deployment for Azure resources

**When to use each:**
- **Terraform**: Multi-cloud, complex workflows, existing Terraform codebase
- **Bicep**: Azure-only, simpler projects, tight Azure integration

## Next Steps

- Compare this exercise with Exercise 2 (manual VM creation) - how much faster is IaC?
- Modify the configuration to use a different VM size or Linux distribution
- Add a second VM to create a VM cluster
- Store Terraform state remotely in Azure Storage Account
- Create Terraform modules to reuse configuration
- Explore Terraform workspaces for managing multiple environments (dev/staging/prod)
- Compare with Exercise 15 (IoT Hub with Terraform) to see Terraform for different services
- Implement Terraform Cloud for team collaboration and CI/CD
- Add data sources to query existing Azure resources
- Use `terraform import` to bring existing resources under Terraform management

## Additional Resources

- [Terraform Documentation](https://www.terraform.io/docs)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Azure VM Documentation](https://docs.microsoft.com/azure/virtual-machines/)
- [HCL Language Spec](https://github.com/hashicorp/hcl)

---

## Reference: Terraform Commands

**Essential commands:**

```bash
# Initialize working directory
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt

# Show execution plan
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy

# Show current state
terraform show

# List resources in state
terraform state list

# Get output values
terraform output

# Refresh state from real infrastructure
terraform refresh
```

**Advanced commands:**

```bash
# Import existing resource
terraform import azurerm_resource_group.example /subscriptions/.../resourceGroups/myRG

# Remove resource from state (doesn't delete real resource)
terraform state rm azurerm_resource_group.example

# Move resource in state (rename)
terraform state mv azurerm_resource_group.old azurerm_resource_group.new

