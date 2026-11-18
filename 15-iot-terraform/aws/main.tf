module "storage_route" {
  source = "../modules/aws-iot-storage-route"

  name_prefix   = var.name_prefix
  storage_level = var.storage_level
}

module "device" {
  source = "../modules/aws-iot-device"

  thing_name = var.device_id
  output_dir = path.module
}

# The endpoint the simulator connects to
data "aws_iot_endpoint" "endpoint" {
  endpoint_type = "iot:Data-ATS"
}
