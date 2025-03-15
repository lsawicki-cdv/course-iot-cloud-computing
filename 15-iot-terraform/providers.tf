terraform {
  required_version = ">= 1.0.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9.0"
    }
  }
}

# The random provider helps create unique resource names
provider "random" {
  # No specific configuration needed
}

# The time provider is useful for creating delay resources
# or time-based conditions when needed
provider "time" {
  # No specific configuration needed
}
