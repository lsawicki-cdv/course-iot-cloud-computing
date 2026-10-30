#!/bin/bash

# Add Docker to sudo group
sudo groupadd docker
sudo usermod -aG docker $USER
sudo reboot

# !!! Close terminal and open a new one

# Build the Docker image
docker build -t my-custom-app:1.0.0 .

# Run the Docker container
docker run --rm -p 8080:80 my-custom-app:1.0.0
