variable "name_prefix" {
  type        = string
  description = "Prefix of the resource names: lowercase letters and digits, starting with a letter, up to 11 characters."

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{0,10}$", var.name_prefix))
    error_message = "name_prefix must start with a lowercase letter and contain only lowercase letters and digits (1-11 characters)."
  }
}

variable "resource_group_name" {
  type        = string
  description = "Resource group for the IoT Hub and the storage account."
}

variable "location" {
  type        = string
  description = "Azure region."
}

variable "storage_level" {
  type        = string
  description = "Route only messages whose 'level' property equals this value. Null routes every message."
  default     = null
}

variable "container_name" {
  type        = string
  description = "Name of the blob container for the telemetry."
  default     = "telemetrydata"
}
