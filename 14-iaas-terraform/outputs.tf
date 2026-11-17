output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

output "public_ip_address" {
  value = azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address
}

output "ssh_command" {
  value = "ssh -i ${module.ssh_key.private_key_file} ${var.username}@${azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address}"
}
