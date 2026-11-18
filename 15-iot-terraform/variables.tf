variable "resource_group_name" {
  type        = string
  description = "Name of the resource group."
  default     = "iot-terraform-rg"
}

variable "location" {
  type        = string
  description = "Azure region."
  default     = "uksouth"
}

variable "name_prefix" {
  type        = string
  description = "Prefix of the resource names: lowercase letters and digits, starting with a letter, up to 11 characters."
  default     = "iot"
}

variable "storage_level" {
  type        = string
  description = "Route only messages with this 'level' property to storage. Null routes everything."
  default     = null
}
