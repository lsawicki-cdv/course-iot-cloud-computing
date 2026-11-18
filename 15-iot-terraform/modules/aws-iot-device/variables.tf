variable "thing_name" {
  type        = string
  description = "Name of the IoT thing; it is also the MQTT client id and part of the topic."
}

variable "output_dir" {
  type        = string
  description = "Directory for the device certificate and private key files."
}
