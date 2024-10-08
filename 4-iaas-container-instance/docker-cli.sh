#!/bin/bash

# Build the Docker image
docker build -t my-custom-app:1.0.0 .

# Run the Docker container
docker run --rm -p 8080:80 my-custom-app:1.0.0

# Investigate the Docker image with Dive
dive build -t my-custom-app:1.0.0 .