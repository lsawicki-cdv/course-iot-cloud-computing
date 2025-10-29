#!/bin/bash
#
# Cloud-init script to install Docker and Docker Compose on Ubuntu 22.04
# This script runs automatically when the VM is first created
#

set -e

echo "==============================================="
echo "Installing Docker and Docker Compose"
echo "==============================================="

# Update package index
apt-get update

# Install prerequisites
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    python3 \
    python3-pip

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
apt-get update

# Install Docker Engine, CLI, and Docker Compose plugin
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add azureuser to docker group
usermod -aG docker azureuser

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Verify installation
docker --version
docker compose version

echo "==============================================="
echo "Docker installation completed successfully!"
echo "==============================================="

# Create a working directory
mkdir -p /home/azureuser/timescaledb-project
chown azureuser:azureuser /home/azureuser/timescaledb-project

echo "Setup complete. You can now deploy TimescaleDB with Docker Compose."
