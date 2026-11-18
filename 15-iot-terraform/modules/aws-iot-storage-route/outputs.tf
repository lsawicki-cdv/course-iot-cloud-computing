output "bucket_name" {
  value = aws_s3_bucket.telemetry.bucket
}

output "rule_name" {
  value = aws_iot_topic_rule.storage_route.name
}
