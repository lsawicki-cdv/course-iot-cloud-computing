# Shared module: an IoT Hub that routes device messages to a blob container.

# Random suffix, so the globally unique names do not collide
resource "random_string" "suffix" {
  length  = 8
  lower   = true
  numeric = true
  upper   = false
  special = false
}

resource "azurerm_iothub" "iothub" {
  name                = "${var.name_prefix}-hub-${random_string.suffix.result}"
  resource_group_name = var.resource_group_name
  location            = var.location

  event_hub_partition_count = 2 # the F1 tier allows exactly 2 (azurerm 4 defaults to 4)

  sku {
    name     = "F1" # Free tier, 8000 messages per day
    capacity = 1
  }

  tags = {
    purpose = "telemetry"
  }
}

resource "azurerm_storage_account" "storage" {
  name                            = "${var.name_prefix}${random_string.suffix.result}"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  min_tls_version                 = "TLS1_2"
}

resource "azurerm_storage_container" "container" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.storage.id
  container_access_type = "private"
}

# Where the hub writes the messages: a batch every 60 seconds
resource "azurerm_iothub_endpoint_storage_container" "telemetry_endpoint" {
  resource_group_name = var.resource_group_name
  iothub_id           = azurerm_iothub.iothub.id
  name                = "telemetryEndpoint"

  connection_string          = azurerm_storage_account.storage.primary_blob_connection_string
  batch_frequency_in_seconds = 60
  max_chunk_size_in_bytes    = 10485760
  container_name             = azurerm_storage_container.container.name
  encoding                   = "JSON"
  file_name_format           = "{iothub}/{partition}/{YYYY}/{MM}/{DD}/{HH}/{mm}"
}

# Without storage_level every message goes to storage; with it, only messages with that 'level' property
resource "azurerm_iothub_route" "telemetry_route" {
  resource_group_name = var.resource_group_name
  iothub_name         = azurerm_iothub.iothub.name
  name                = "telemetryRoute"
  source              = "DeviceMessages"
  condition           = var.storage_level == null ? "true" : "level=\"${var.storage_level}\""
  endpoint_names      = [azurerm_iothub_endpoint_storage_container.telemetry_endpoint.name]
  enabled             = true
}
