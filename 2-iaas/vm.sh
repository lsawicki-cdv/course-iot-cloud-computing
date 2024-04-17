#!/bin/bash
# Use this for your user data (script from top to bottom)
# install httpd (Linux 2 version)
sudo apt update -y
# install ngnix server
sudo apt install nginx -y
# start ngnix server
sudo systemctl start nginx
# enable ngnix server
sudo systemctl enable nginx
# change welcome page to custom page
echo "<h1>Hello World from $(hostname -f)</h1>" | sudo tee /var/www/html/index.html