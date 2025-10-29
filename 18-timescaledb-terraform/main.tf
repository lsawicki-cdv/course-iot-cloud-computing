# Resource Group
resource "azurerm_resource_group" "timescaledb_rg" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = "learning"
    project     = "timescaledb-iot"
  }
}

# Virtual Network
resource "azurerm_virtual_network" "vnet" {
  name                = "timescaledb-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.timescaledb_rg.location
  resource_group_name = azurerm_resource_group.timescaledb_rg.name
}

# Subnet
resource "azurerm_subnet" "subnet" {
  name                 = "timescaledb-subnet"
  resource_group_name  = azurerm_resource_group.timescaledb_rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Public IP
resource "azurerm_public_ip" "public_ip" {
  name                = "timescaledb-public-ip"
  location            = azurerm_resource_group.timescaledb_rg.location
  resource_group_name = azurerm_resource_group.timescaledb_rg.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = {
    environment = "learning"
  }
}

# Network Security Group
resource "azurerm_network_security_group" "nsg" {
  name                = "timescaledb-nsg"
  location            = azurerm_resource_group.timescaledb_rg.location
  resource_group_name = azurerm_resource_group.timescaledb_rg.name

  # SSH
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

  # API (Flask)
  security_rule {
    name                       = "API"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # PostgreSQL/TimescaleDB (optional, for external access)
  security_rule {
    name                       = "PostgreSQL"
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    environment = "learning"
  }
}

# Network Interface
resource "azurerm_network_interface" "nic" {
  name                = "timescaledb-nic"
  location            = azurerm_resource_group.timescaledb_rg.location
  resource_group_name = azurerm_resource_group.timescaledb_rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.public_ip.id
  }
}

# Associate NSG with Network Interface
resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# Virtual Machine
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "timescaledb-vm"
  location            = azurerm_resource_group.timescaledb_rg.location
  resource_group_name = azurerm_resource_group.timescaledb_rg.name
  size                = var.vm_size
  admin_username      = var.admin_username

  network_interface_ids = [
    azurerm_network_interface.nic.id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    name                 = "timescaledb-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 64
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # Cloud-init script to install Docker
  custom_data = base64encode(file("${path.module}/docker-setup.sh"))

  tags = {
    environment = "learning"
    purpose     = "timescaledb-iot"
  }
}
