output "bucket_name" {
  value = module.storage_route.bucket_name
}

output "rule_name" {
  value = module.storage_route.rule_name
}

output "iot_endpoint" {
  description = "Put this value into iot_endpoint in the simulator."
  value       = data.aws_iot_endpoint.endpoint.endpoint_address
}

output "device_id" {
  value = module.device.thing_name
}
