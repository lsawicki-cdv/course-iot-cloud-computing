# Generate the SSH key of the VM with the shared module (the same module as in the AWS version)
module "ssh_key" {
  source           = "./modules/ssh-key"
  private_key_file = "${path.module}/ssh-key.pem"
}
