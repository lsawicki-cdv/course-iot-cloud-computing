## Azure VM with Terraform

### Tested environments
Ubuntu 22.04
Terraform v1.11.0

### Exercise - Deploy an Azure VM using Terraform in Cloud Shell

This exercise will guide you through creating an Azure Virtual Machine using Terraform in the Azure Cloud Shell. You'll configure port 80 for HTTP access and install an nginx web server using a custom script.

### Task Steps

1. Open the Azure Cloud Shell by navigating to Azure Portal and clicking the Cloud Shell icon (>_) in the top navigation bar
2. Make sure you are using the Bash environment in Cloud Shell
3. Create a new directory for your Terraform project and navigate to it
```bash
    mkdir terraform-vm
    cd terraform-vm
```
4. Clone the repository (https://github.com/lsawicki-cdv/course-iot-cloud-computing.git) to the `terraform-vm` directory **or** create the following Terraform configuration files using the nano command:
   1. Create providers.tf using `nano providers.tf` and copy following content:
    ```bash
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
    2. Create variables.tf using `nano variables.tf` and copy following content:
   ```bash
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
    3. Create main.tf using `nano main.tf` and copy following content:
    ```bash
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
    4. Create outputs.tf using `nano outputs.tf` and copy following content:
    ```bash
        output "resource_group_name" {
        value = azurerm_resource_group.rg.name
        }

        output "public_ip_address" {
        value = azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address
        }
    ```
    5. Create ssh.tf using `nano ssh.tf` and copy following content:
    ```bash
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
5. Initialize the Terraform working directory
```bash
terraform init -upgrade
```
6. Review the Terraform plan to see what resources will be created
```bash
terraform plan -out main.tfplan
```
7. Apply the Terraform configuration to create the resources
```bash
terraform apply main.tfplan
```
8. Verify on Azure if the resources where created properly.
9. Adjust the terraform files so:
   1. The Network security group has the port 80 (HTTP) open
   2. the Bash script from: https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh is installed during deployment
10. Verify the web server is running by accessing the VM's public IP address in a web browser
11. When finished, clean up all resources to avoid unnecessary costs
```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```
### Important Notes

The script that installs nginx is located at: https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/2-iaas/vm.sh
The Network Security Group is configured to allow both SSH (port 22) and HTTP (port 80) traffic
The terraform configuration automatically generates SSH keys for secure access
The VM size (Standard_B1s) is suitable for testing as it's included in the free tier
