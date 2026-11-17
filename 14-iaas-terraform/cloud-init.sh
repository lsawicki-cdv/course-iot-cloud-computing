#!/bin/bash
# Install and configure nginx web server (runs once, on the first boot of the VM)
# Shared by the Azure (custom_data) and the AWS (user_data) configuration
apt-get update -y
apt-get install -y nginx
systemctl enable --now nginx
echo "<h1>Hello World from $(hostname -f)</h1>" > /var/www/html/index.html
