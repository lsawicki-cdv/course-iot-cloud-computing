variable "name_prefix" {
  type        = string
  description = "Prefix of the resource names: lowercase letters and digits, starting with a letter, up to 11 characters."

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{0,10}$", var.name_prefix))
    error_message = "name_prefix must start with a lowercase letter and contain only lowercase letters and digits (1-11 characters)."
  }
}

variable "storage_level" {
  type        = string
  description = "Store only messages whose 'level' user property equals this value. Null stores every message."
  default     = null
}
