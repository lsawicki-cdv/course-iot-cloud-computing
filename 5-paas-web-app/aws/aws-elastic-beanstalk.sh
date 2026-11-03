#!/bin/bash

# Variables
REGION="eu-west-2"
APP_NAME="flask-webapp"
ENV_NAME="flask-webapp-env"
SIZE="t3.micro"

# Install the Elastic Beanstalk CLI
pip3 install --user awsebcli
export PATH=$PATH:~/.local/bin

# Copy the Flask app out of the git repository, so `eb deploy` uploads the files and not the last git commit
git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
cp -r course-iot-cloud-computing/5-paas-web-app ~/$APP_NAME
cd ~/$APP_NAME

# Tell Elastic Beanstalk how to start the app
echo "web: gunicorn app:app" > Procfile

# Create the Elastic Beanstalk application
eb init $APP_NAME --platform python-3.11 --region $REGION

# Create an environment with a single VM (no load balancer) and deploy the app
eb create $ENV_NAME --single --instance_type $SIZE

# Get the URL of the app
APP_URL=$(eb status | grep CNAME | awk '{print $2}')

curl --connect-timeout 5 http://$APP_URL

# Show the logs of the app
# eb logs

# Redeploy the app after a change
# eb deploy

# Delete the environment and the application
# eb terminate $ENV_NAME --all --force
