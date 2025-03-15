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
