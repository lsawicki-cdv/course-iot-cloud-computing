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
