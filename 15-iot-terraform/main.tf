resource "azurerm_resource_group" "iot_rg" {
  name     = var.resource_group_name
  location = var.location
}

# IoT Hub, storage account and the route between them
module "iot_storage_route" {
  source = "./modules/azure-iot-storage-route"

  name_prefix         = var.name_prefix
  resource_group_name = azurerm_resource_group.iot_rg.name
  location            = azurerm_resource_group.iot_rg.location
  storage_level       = var.storage_level
}
