variable "region" {
  type        = string
  description = "AWS region."
  default     = "eu-west-2"
}

variable "name_prefix" {
  type        = string
  description = "Prefix of the resource names: lowercase letters and digits, starting with a letter, up to 11 characters."
  default     = "iot"
}

variable "device_id" {
  type        = string
  description = "Name of the IoT thing. The simulator's device_id must be the same."
  default     = "terraform-device-01"
}

variable "storage_level" {
  type        = string
  description = "Store only messages whose 'level' user property equals this value. Null stores every message."
  default     = null
}
