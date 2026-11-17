# Terraform Basics

This page is shared by both versions of Exercise 14: [Azure](readme.md) and [AWS](aws/readme.md). It explains what Terraform is and how it works; the two readmes contain only the steps for their cloud.

## What is Terraform?

**Terraform** is an open-source Infrastructure as Code tool created by HashiCorp. It's:
- **Cloud-agnostic** - Works with AWS, Azure, GCP, and 100+ other providers
- **Declarative** - Describe what you want, Terraform figures out how to create it
- **State-managed** - Tracks infrastructure state to detect and manage changes
- **Widely adopted** - Industry standard for multi-cloud IaC

"Cloud-agnostic" doesn't mean that one configuration runs on every cloud: each cloud has its own resources (`azurerm_linux_virtual_machine` vs `aws_instance`). What stays the same is the language, the workflow and the tools - and you can share code between clouds, like this exercise does with the SSH key module and the nginx script.

### Terraform vs Bicep vs CloudFormation

| Feature | Terraform | Bicep (Exercise 12-13) | CloudFormation (AWS versions of 12-13) |
|---------|-----------|------------------------|-----------------------------------------|
| Cloud Support | Multi-cloud (AWS, Azure, GCP, etc.) | Azure only | AWS only |
| Language | HCL (HashiCorp Configuration Language) | Bicep DSL | YAML / JSON |
| State Management | State file (`terraform.tfstate`) | Managed by Azure | Managed by AWS (the stack) |
| Preview of changes | `terraform plan` | What-if | Change set |
| Rollback on failure | No - fix and apply again | No | Automatic |
| Provider Ecosystem | 1000+ providers (also GitHub, Cloudflare, ...) | Azure services only | AWS services only |

Use **Bicep / CloudFormation** if: You only work with one cloud and want tight integration
Use **Terraform** if: You work with multiple clouds or need provider flexibility

## How the Exercise is Organized

```
14-iaas-terraform/
  ├── cloud-init.sh            shared: installs nginx on the first boot of the VM
  ├── modules/ssh-key/main.tf  shared: generates the SSH key of the VM
  ├── providers.tf             Azure: Terraform and provider versions
  ├── variables.tf             Azure: input variables
  ├── main.tf                  Azure: the resources
  ├── outputs.tf               Azure: values shown after deployment
  ├── ssh.tf                   Azure: uses the ssh-key module
  └── aws/
      ├── providers.tf         AWS: Terraform and provider versions
      ├── variables.tf         AWS: input variables
      ├── main.tf              AWS: the resources
      ├── outputs.tf           AWS: values shown after deployment
      └── ssh.tf               AWS: uses the same ssh-key module
```

Terraform reads **all `.tf` files of the directory** you run it in; the split into files is only for readability. The Azure configuration runs in `14-iaas-terraform`, the AWS configuration in `14-iaas-terraform/aws`.

### The Shared SSH Key Module

A **module** is a directory with `.tf` files that other configurations call. `modules/ssh-key/main.tf` works on any cloud, because it only uses two cloud-independent providers:
- `tls` - generates the key pair (`tls_private_key`)
- `local` - saves the private key to `ssh-key.pem` with permissions `0600` (`local_sensitive_file`)

Both `ssh.tf` files call it the same way:

```hcl
module "ssh_key" {
  source           = "./modules/ssh-key"   # "../modules/ssh-key" in the AWS version
  private_key_file = "${path.module}/ssh-key.pem"
}
```

and the VM uses its output `module.ssh_key.public_key_openssh`. The module's outputs are its "return values", like the outputs of the whole configuration.

**Note:** Terraform keeps the private key in its state file too. That's fine for an exercise; in real projects, use keys you create yourself, or no SSH at all (Azure Bastion, AWS Systems Manager Session Manager).

### The Shared nginx Script

`cloud-init.sh` is a shell script that **cloud-init** runs once, on the first boot of the VM. Both clouds run cloud-init in their Ubuntu images; only the name of the setting differs: `custom_data` on Azure, `user_data` on AWS.

```bash
#!/bin/bash
apt-get update -y
apt-get install -y nginx
systemctl enable --now nginx
echo "<h1>Hello World from $(hostname -f)</h1>" > /var/www/html/index.html
```

The script runs as `root`, so it doesn't need `sudo`.

## The Terraform Workflow

```
terraform init  →  terraform plan  →  terraform apply  →  (change the files, plan, apply again)  →  terraform destroy
```

**`terraform init -upgrade`** - prepares the directory:
- Downloads the providers (plugins that talk to the cloud APIs) into `.terraform/`
- Loads the modules (here: `ssh-key`)
- Writes `.terraform.lock.hcl` with the exact provider versions
- `-upgrade` picks the newest versions allowed by `version = "~>..."` in `providers.tf`

**`terraform plan -out main.tfplan`** - shows what would change:
- Reads the configuration and the state, and asks the cloud what really exists
- Lists each resource with `+` (create), `~` (update in place), `-/+` (replace: delete and create) or `-` (delete)
- Saves the plan to `main.tfplan`, so `apply` does exactly what you reviewed

**`terraform apply main.tfplan`** - makes the changes from the plan and saves the result in the state. Terraform creates independent resources in parallel and waits for the ones others depend on.

**`terraform plan -destroy -out main.destroy.tfplan`** and **`terraform apply main.destroy.tfplan`** - delete everything in the state (the same as `terraform destroy`, but you review the plan first).

**Update in place or replace?** Some settings can be changed on a running resource (a firewall rule); others can't, so Terraform deletes the resource and creates a new one. The plan says which: `must be replaced` and `# forces replacement` next to the setting. The VM's first-boot script (`custom_data` / `user_data`) forces a replacement, so the VM gets a new public IP address.

## Key Concepts

**Resources**: Building blocks of infrastructure (`<provider>_<type>` and your name for it)
```hcl
resource "azurerm_virtual_network" "my_terraform_network" {   # or "aws_vpc"
  name = "myVnet"
  ...
}
```

**Data sources**: Read something that exists already, without managing it
```hcl
data "aws_availability_zones" "available" {
  state = "available"
}
```

**Variables**: Parameterize configuration (override with `terraform plan -var name=value`)
```hcl
variable "username" {
  default = "azureadmin"
}
```

**Outputs**: Return values from deployment (`terraform output`, `terraform output -raw <name>`)
```hcl
output "public_ip_address" {
  value = azurerm_linux_virtual_machine.my_terraform_vm.public_ip_address
}
```

**Dependencies**: Terraform automatically handles order
- Implicit: References (`azurerm_resource_group.rg.name`, `module.ssh_key.public_key_openssh`) create dependencies
- Explicit: Use `depends_on` when needed

## Terraform State

**List resources in state:**

```bash
terraform state list
```

**View all managed resources and their current attributes:**

```bash
terraform show
```

**What is Terraform state?**
- Tracks mapping between configuration and real resources (e.g. `aws_instance.my_terraform_vm` ↔ `i-0abc...`)
- Stored in `terraform.tfstate` file in the directory you run Terraform in
- Contains resource IDs, attributes, metadata - and secrets, like the private SSH key
- **Important:** Never manually edit state file! And don't lose it: without it, Terraform doesn't know what it created, and you have to delete the resources by hand
- In production, store state remotely (Azure Storage, Amazon S3, HCP Terraform), so a team shares one state with locking

## Common Troubleshooting

### Terraform init fails with "could not query provider registry"

- **Check internet connection**: Cloud Shell needs internet access
- **Clear cache**: Delete `.terraform` directory and run `terraform init` again
- **Update Terraform**: Run `terraform version` to check version (1.5 or newer is required)

### Plan shows "Error: Reference to undeclared resource"

- **Check resource names**: Ensure all references match resource names exactly
- **Check file syntax**: Run `terraform validate` to check syntax
- **Check the directory**: Run Terraform in the directory with the `.tf` files

### "Saved plan is stale"

- **The state changed after you created the plan**: Run `terraform plan -out main.tfplan` again, then apply

### Apply fails with "A resource with the ID already exists"

- **Check state file**: You might have state conflicts (e.g. you deleted `terraform.tfstate`)
- **Import existing resource**: Use `terraform import` if resource exists
- **Delete and recreate**: Delete the resource in the cloud console and apply again

### Cannot access the web server after deployment

- **Wait 2-3 minutes**: The cloud-init script takes time to run after the VM starts
- **Check the HTTP rule**: Port 80 must be open (Part 4 of the exercise)
- **Check the script ran**: SSH to the VM and run `sudo cat /var/log/cloud-init-output.log` and `sudo systemctl status nginx`
- **Check script format**: `cloud-init.sh` must have Unix line endings (LF, not CRLF) and start with `#!/bin/bash`

### SSH fails

- **"Connection refused" or a timeout right after apply**: The VM is still booting - wait a minute
- **"Permission denied (publickey)"**: Use the user from `terraform output ssh_command` and the key `ssh-key.pem` from the same directory
- **"UNPROTECTED PRIVATE KEY FILE"**: Run `chmod 600 ssh-key.pem`

## Reference: Terraform Commands

**Essential commands:**

```bash
# Initialize working directory
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt

# Show execution plan
terraform plan

# Apply changes
terraform apply

# Destroy infrastructure
terraform destroy

# Show current state
terraform show

# List resources in state
terraform state list

# Get output values
terraform output

# Refresh state from real infrastructure
terraform apply -refresh-only
```

**Advanced commands:**

```bash
# Import existing resource
terraform import azurerm_resource_group.example /subscriptions/.../resourceGroups/myRG

# Remove resource from state (doesn't delete real resource)
terraform state rm azurerm_resource_group.example

# Move resource in state (rename)
terraform state mv azurerm_resource_group.old azurerm_resource_group.new
```

## Additional Resources

- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Modules](https://developer.hashicorp.com/terraform/language/modules)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [cloud-init Documentation](https://cloudinit.readthedocs.io/)
