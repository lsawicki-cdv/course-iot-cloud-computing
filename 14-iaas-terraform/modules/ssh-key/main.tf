# Shared module: generates an SSH key pair for a VM and saves the private key to a file.
# Used by both the Azure configuration (../../ssh.tf) and the AWS configuration (../../aws/ssh.tf).

terraform {
  required_providers {
    tls = {
      source  = "hashicorp/tls"
      version = "~>4.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~>2.5"
    }
  }
}

variable "private_key_file" {
  type        = string
  description = "Path of the file to save the private key to."
}

# The key pair (note: Terraform keeps the private key in its state file too)
resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Save the private key, readable only by you (ssh refuses keys that others can read)
resource "local_sensitive_file" "private_key" {
  content         = tls_private_key.ssh.private_key_openssh
  filename        = var.private_key_file
  file_permission = "0600"
}

output "public_key_openssh" {
  description = "The public key in the OpenSSH format, for the VM."
  value       = tls_private_key.ssh.public_key_openssh
}

output "private_key_file" {
  description = "The file with the private key."
  value       = local_sensitive_file.private_key.filename
}
