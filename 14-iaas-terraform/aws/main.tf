# Find the newest Ubuntu 26.04 image (AMI) of the region, published by Canonical
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/26.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

# Find the availability zones (data centers) of the region
data "aws_availability_zones" "available" {
  state = "available"
}

# Create virtual network
resource "aws_vpc" "my_terraform_network" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "myVpc"
  }
}

# Create subnet (VMs in it get a public IP address)
resource "aws_subnet" "my_terraform_subnet" {
  vpc_id                  = aws_vpc.my_terraform_network.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "mySubnet"
  }
}

# Connect the virtual network to the internet (on Azure, every virtual network has this built in)
resource "aws_internet_gateway" "my_terraform_gateway" {
  vpc_id = aws_vpc.my_terraform_network.id

  tags = {
    Name = "myInternetGateway"
  }
}

# Send the internet traffic of the subnet through the gateway
resource "aws_route_table" "my_terraform_route_table" {
  vpc_id = aws_vpc.my_terraform_network.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.my_terraform_gateway.id
  }

  tags = {
    Name = "myRouteTable"
  }
}

resource "aws_route_table_association" "my_terraform_route_table_association" {
  subnet_id      = aws_subnet.my_terraform_subnet.id
  route_table_id = aws_route_table.my_terraform_route_table.id
}

# Create security group and rule
resource "aws_security_group" "my_terraform_sg" {
  name        = "mySecurityGroup"
  description = "Security group of myVM"
  vpc_id      = aws_vpc.my_terraform_network.id

  ingress {
    description = "SSH"
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outgoing traffic (e.g. to download packages)
  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Register the public key of the shared ssh-key module in EC2
resource "aws_key_pair" "my_terraform_key" {
  key_name_prefix = "myKey-"
  public_key      = module.ssh_key.public_key_openssh
}

# Create virtual machine
resource "aws_instance" "my_terraform_vm" {
  ami                    = nonsensitive(data.aws_ssm_parameter.ubuntu.value)
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.my_terraform_subnet.id
  vpc_security_group_ids = [aws_security_group.my_terraform_sg.id]
  key_name               = aws_key_pair.my_terraform_key.key_name

  # Require IMDSv2 for the instance metadata (the secure version)
  metadata_options {
    http_tokens = "required"
  }

  tags = {
    Name = "myVM"
  }
}
