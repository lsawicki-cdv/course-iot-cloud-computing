output "thing_name" {
  value = aws_iot_thing.device.name
}

output "topic" {
  value = local.topic
}

output "certificate_file" {
  value = local_sensitive_file.certificate.filename
}

output "private_key_file" {
  value = local_sensitive_file.private_key.filename
}
