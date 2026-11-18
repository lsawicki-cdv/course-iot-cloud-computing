# Shared module: an IoT thing with its own certificate and a policy limited to its client id and topic.

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  # The topic convention shared with the rule's filter and the simulator
  topic = "devices/${var.thing_name}/messages/events/"
  arn   = "arn:aws:iot:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"
}

# IoT Core creates the key pair and signs the certificate
resource "aws_iot_certificate" "device" {
  active = true
}

resource "aws_iot_thing" "device" {
  name = var.thing_name
}

resource "aws_iot_policy" "device" {
  name = "${var.thing_name}-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "iot:Connect"
        Resource = "${local.arn}:client/${var.thing_name}"
      },
      {
        Effect   = "Allow"
        Action   = "iot:Publish"
        Resource = "${local.arn}:topic/${local.topic}"
      }
    ]
  })
}

resource "aws_iot_policy_attachment" "device" {
  policy = aws_iot_policy.device.name
  target = aws_iot_certificate.device.arn
}

resource "aws_iot_thing_principal_attachment" "device" {
  thing     = aws_iot_thing.device.name
  principal = aws_iot_certificate.device.arn
}

# The files the simulator reads (the private key stays in the Terraform state too)
resource "local_sensitive_file" "certificate" {
  filename        = "${var.output_dir}/device.pem.crt"
  content         = aws_iot_certificate.device.certificate_pem
  file_permission = "0600"
}

resource "local_sensitive_file" "private_key" {
  filename        = "${var.output_dir}/private.pem.key"
  content         = aws_iot_certificate.device.private_key
  file_permission = "0600"
}
