variable "region" {
  type        = string
  default     = "eu-west-2"
  description = "AWS region of all resources."
}

variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "Size of the VM (t3.micro is Free Tier eligible; use t2.micro if t3.micro isn't in your region)."
}

variable "username" {
  type        = string
  description = "The user of the Ubuntu image (AWS images come with this user; it can't be changed like on Azure)."
  default     = "ubuntu"
}
