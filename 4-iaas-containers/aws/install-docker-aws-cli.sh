#!/bin/bash

# Install Docker engine and allow the default user to run it without sudo
apt-get update -y
apt-get install -y docker.io
usermod -aG docker ubuntu

# Install AWS CLI
snap install aws-cli --classic
