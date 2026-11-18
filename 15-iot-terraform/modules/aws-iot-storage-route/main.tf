# Shared module: an AWS IoT rule that stores device messages in an S3 bucket.

data "aws_caller_identity" "current" {}

# The bucket for the telemetry (AWS adds a unique suffix to the prefix)
resource "aws_s3_bucket" "telemetry" {
  bucket_prefix = "${var.name_prefix}-telemetry-"
  force_destroy = true # destroy deletes the stored telemetry too
}

resource "aws_s3_bucket_public_access_block" "telemetry" {
  bucket                  = aws_s3_bucket.telemetry.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Allow only encrypted (HTTPS) access to the bucket
resource "aws_s3_bucket_policy" "telemetry" {
  bucket = aws_s3_bucket.telemetry.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.telemetry.arn, "${aws_s3_bucket.telemetry.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.telemetry]
}

# The role of the rule: AWS IoT may only write objects to the bucket
resource "aws_iam_role" "storage_route" {
  name_prefix = "${var.name_prefix}-storage-route-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "iot.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
    }]
  })
}

resource "aws_iam_role_policy" "write_telemetry" {
  name = "write-telemetry"
  role = aws_iam_role.storage_route.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:PutObject"
      Resource = "${aws_s3_bucket.telemetry.arn}/*"
    }]
  })
}

# The rule (the counterpart of the IoT Hub route): write each message to the bucket as a JSON file.
# With storage_level set, only the messages with that 'level' user property are selected.
resource "aws_iot_topic_rule" "storage_route" {
  name        = "${var.name_prefix}_storage_route"
  enabled     = true
  sql_version = "2016-03-23"
  sql = join(" ", compact([
    "SELECT *, topic(2) AS device_id, timestamp() AS received_at FROM 'devices/+/messages/events/'",
    var.storage_level == null ? "" : "WHERE get(get_user_properties('level'), 0) = '${var.storage_level}'",
  ]))

  s3 {
    bucket_name = aws_s3_bucket.telemetry.bucket
    key         = "$${topic(2)}/$${parse_time(\"yyyy/MM/dd/HH/mm\", timestamp())}/$${newuuid()}.json"
    role_arn    = aws_iam_role.storage_route.arn
  }

  # The role policy must exist before the rule uses the role
  depends_on = [aws_iam_role_policy.write_telemetry]
}
