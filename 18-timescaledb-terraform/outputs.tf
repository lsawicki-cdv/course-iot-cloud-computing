output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.timescaledb_rg.name
}

output "vm_public_ip" {
  description = "Public IP address of the VM"
  value       = azurerm_public_ip.public_ip.ip_address
}

output "ssh_command" {
  description = "SSH command to connect to the VM"
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.public_ip.ip_address}"
}

output "api_url" {
  description = "API endpoint URL"
  value       = "http://${azurerm_public_ip.public_ip.ip_address}:5000"
}

output "connection_instructions" {
  description = "Instructions for connecting to the VM and services"
  value       = <<-EOT

  ========================================
  TimescaleDB VM Deployed Successfully!
  ========================================

  SSH Connection:
    ssh ${var.admin_username}@${azurerm_public_ip.public_ip.ip_address}

  After connecting, run:
    cd ~/
    git clone <repository-url>  # or copy files with scp
    cd 18-timescaledb-terraform
    docker compose up -d
    python3 init_database.py
    python3 generate_data.py --days 30 --sensors 10

  API Endpoints:
    http://${azurerm_public_ip.public_ip.ip_address}:5000/api/sensors
    http://${azurerm_public_ip.public_ip.ip_address}:5000/api/sensors/sensor_001/current

  Database Connection:
    docker exec -it timescaledb psql -U postgres -d iotdata

  EOT
}
