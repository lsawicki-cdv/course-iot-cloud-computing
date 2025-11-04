## Azure IoT Hub with Terraform

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

### Tested environments
Ubuntu 24.04
Terraform v1.11.0

### Exercise - Deploy an Azure Iot Hub using Terraform in Cloud Shell

This exercise will guide you through creating an Azure Iot Hub with Azure Blob Storage using Terraform in the Azure Cloud Shell.

### Task Steps

1. Open the Azure Cloud Shell by navigating to Azure Portal and clicking the Cloud Shell icon (>_) in the top navigation bar
2. Make sure you are using the Bash environment in Cloud Shell
3. Create a new directory for your Terraform project and navigate to it
```bash
    mkdir azure-iot-terraform
    cd azure-iot-terraform
```
4. Clone the repository (https://github.com/lsawicki-cdv/course-iot-cloud-computing.git) to the `azure-iot-terraform` directory **or** create the following Terraform configuration files using the nano command:
   1. Create providers.tf using `nano providers.tf` and copy following content:
    ```bash
        terraform {
            required_providers {
                azurerm = {
                    source  = "hashicorp/azurerm"
                    version = "~> 3.0"
                }
            }
        }

        provider "azurerm" {
            features {}
        }

    ```
    2. Create variables.tf using `nano variables.tf` and copy following content:
   ```bash
        variable "resource_group_name" {
        description = "Name of the resource group"
        default     = "iot-terraform-rg"
        }

        variable "location" {
        description = "Azure region"
        default     = "uksouth"  # Change to your allowed region if needed
        }

        variable "iot_hub_name" {
        description = "Name of the IoT Hub"
        default     = "terraform-iot-hub"
        }

        variable "storage_account_name" {
        description = "Name of the storage account"
        default     = "terraformiotstorage"
        }

        variable "container_name" {
        description = "Name of the blob container"
        default     = "telemetrydata"
        }

    ```
    3. Create main.tf using `nano main.tf` and copy following content:
    ```bash
        # Create a resource group
        resource "azurerm_resource_group" "iot_rg" {
        name     = var.resource_group_name
        location = var.location
        }

        resource "azurerm_iothub" "iothub" {
        name                = var.iot_hub_name
        resource_group_name = azurerm_resource_group.iot_rg.name
        location            = azurerm_resource_group.iot_rg.location

        sku {
            name     = "F1" # Free tier, 8000 messages per day
            capacity = "1"
        }

        tags = {
            purpose = "telemetry"
        }
        }

        resource "azurerm_storage_account" "storage" {
        name                     = var.storage_account_name
        resource_group_name      = azurerm_resource_group.iot_rg.name
        location                 = azurerm_resource_group.iot_rg.location
        account_tier             = "Standard"
        account_replication_type = "LRS"
        }

        resource "azurerm_storage_container" "container" {
        name                  = var.container_name
        storage_account_name  = azurerm_storage_account.storage.name
        container_access_type = "private"
        }

        resource "azurerm_iothub_endpoint_storage_container" "telemetry_endpoint" {
        resource_group_name = azurerm_resource_group.iot_rg.name
        iothub_id           = azurerm_iothub.iothub.id
        name                = "telemetryEndpoint"

        connection_string          = azurerm_storage_account.storage.primary_blob_connection_string
        batch_frequency_in_seconds = 60
        max_chunk_size_in_bytes    = 10485760
        container_name             = azurerm_storage_container.container.name
        encoding                   = "JSON"
        file_name_format           = "{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}"
        }

        resource "azurerm_iothub_route" "telemetry_route" {
        resource_group_name = azurerm_resource_group.iot_rg.name
        iothub_name         = azurerm_iothub.iothub.name
        name                = "telemetryRoute"
        source              = "DeviceMessages"
        condition           = "true"
        endpoint_names      = [azurerm_iothub_endpoint_storage_container.telemetry_endpoint.name]
        enabled             = true
        }

        # Create IoT Hub shared access policy
        resource "azurerm_iothub_shared_access_policy" "policy" {
        name                = "terraform-policy"
        resource_group_name = azurerm_resource_group.iot_rg.name
        iothub_name         = azurerm_iothub.iothub.name

        registry_read   = true
        registry_write  = true
        service_connect = true
        device_connect  = true
        }

    ```
    4. Create outputs.tf using `nano outputs.tf` and copy following content:
    ```bash
        output "iot_hub_name" {
            value = azurerm_iothub.iothub.name
        }

        output "iot_hub_connection_string" {
            value     = azurerm_iothub_shared_access_policy.policy.primary_connection_string
            sensitive = true
        }

        output "storage_account_name" {
            value = azurerm_storage_account.storage.name
        }

        output "blob_container_name" {
            value = azurerm_storage_container.container.name
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
9. Create a test device on the Azure Iot Hub and copy the Primary Connection String
10. Paste the connection string to `simple_azure_device_simulator.py`
11. On **macOS/Linux** type in the terminal the following commands
   ```bash
      python3 -m venv .venv
      source .venv/bin/activate
   ```
12. On **Windows** type in the terminal the following commands
   ```powershell
      py -m venv .venv
      .venv\scripts\activate
   ```
13. Install dependencies: `pip install -r requirements.txt`
14. Run the simulator 'python simple_azure_device_simulator.py`
15. Check on the Azure Blob Storage if there are any data.
16. When finished, clean up all resources to avoid unnecessary costs
```bash
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```
