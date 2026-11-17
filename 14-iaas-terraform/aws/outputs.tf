output "instance_id" {
  value = aws_instance.my_terraform_vm.id
}

output "public_ip_address" {
  value = aws_instance.my_terraform_vm.public_ip
}

output "ssh_command" {
  value = "ssh -i ${module.ssh_key.private_key_file} ${var.username}@${aws_instance.my_terraform_vm.public_ip}"
}
