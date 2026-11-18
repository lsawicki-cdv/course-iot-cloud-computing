output "resource_group_name" {
  value = azurerm_resource_group.iot_rg.name
}

output "iot_hub_name" {
  value = module.iot_storage_route.iot_hub_name
}

output "storage_account_name" {
  value = module.iot_storage_route.storage_account_name
}

output "blob_container_name" {
  value = module.iot_storage_route.container_name
}
