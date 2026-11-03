#!/bin/bash

# Install Docker engine with the Docker Compose plugin and allow the default user to run it without sudo
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
