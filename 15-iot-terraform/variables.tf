variable "resource_group_name" {
  description = "Name of the resource group"
  default     = "iot-terraform-rg"
}

variable "location" {
  description = "Azure region"
  default     = "uksouth"
}

variable "iot_hub_name" {
  description = "Name of the IoT Hub"
  default     = "terraform-iot-hub"
}

variable "storage_account_name" {
  description = "Name of the storage account"
  default     = "terraformiotstorage"
}

variable "container_name" {
  description = "Name of the blob container"
  default     = "telemetrydata"
}
