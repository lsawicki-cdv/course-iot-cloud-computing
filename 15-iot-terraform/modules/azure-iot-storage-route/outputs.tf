output "iot_hub_name" {
  description = "Name of the IoT Hub."
  value       = azurerm_iothub.iothub.name
}

output "storage_account_name" {
  description = "Name of the storage account."
  value       = azurerm_storage_account.storage.name
}

output "container_name" {
  description = "Name of the blob container."
  value       = azurerm_storage_container.container.name
}
