terraform {
  required_version = ">=1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~>6.0"
    }
  }
}

provider "aws" {
  region = var.region

  # Tags added to every resource, so you can find what Terraform created
  default_tags {
    tags = {
      Project = "terraform-vm"
    }
  }
}
