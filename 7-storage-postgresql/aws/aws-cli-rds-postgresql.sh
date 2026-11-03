#!/bin/bash

# Variables
REGION="eu-west-2"
DB_INSTANCE_ID="iot-postgres"
ADMIN_USER="iotadmin"
ADMIN_PASSWORD="<your-password>"
DATABASE_NAME="iotdata"
MY_IP="<your-public-ip>"
CLOUDSHELL_IP=$(curl -s https://checkip.amazonaws.com)

# Install psql (the PostgreSQL terminal client) in CloudShell
sudo dnf install -y postgresql15

# Create a security group that allows PostgreSQL (port 5432) from your computer and from CloudShell
SECURITY_GROUP_ID=$(aws ec2 create-security-group \
  --region $REGION \
  --group-name ${DB_INSTANCE_ID}-sg \
  --description "Security group for $DB_INSTANCE_ID" \
  --query GroupId \
  --output text)

aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $MY_IP/32

aws ec2 authorize-security-group-ingress \
  --region $REGION \
  --group-id $SECURITY_GROUP_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $CLOUDSHELL_IP/32

# Create a PostgreSQL DB instance (db.t3.micro, 20 GB) with a database
aws rds create-db-instance \
  --region $REGION \
  --db-instance-identifier $DB_INSTANCE_ID \
  --engine postgres \
  --engine-version 16 \
  --db-instance-class db.t3.micro \
  --allocated-storage 20 \
  --storage-type gp2 \
  --master-username $ADMIN_USER \
  --master-user-password "$ADMIN_PASSWORD" \
  --db-name $DATABASE_NAME \
  --vpc-security-group-ids $SECURITY_GROUP_ID \
  --publicly-accessible \
  --no-multi-az \
  --backup-retention-period 1

aws rds wait db-instance-available --region $REGION --db-instance-identifier $DB_INSTANCE_ID

# Get the hostname (endpoint) of the DB instance
DB_HOST=$(aws rds describe-db-instances \
  --region $REGION \
  --db-instance-identifier $DB_INSTANCE_ID \
  --query "DBInstances[0].Endpoint.Address" \
  --output text)

# Connect with psql
psql "host=$DB_HOST port=5432 dbname=$DATABASE_NAME user=$ADMIN_USER sslmode=require"

# Delete the DB instance and the security group
# aws rds delete-db-instance --region $REGION --db-instance-identifier $DB_INSTANCE_ID --skip-final-snapshot --delete-automated-backups
# aws rds wait db-instance-deleted --region $REGION --db-instance-identifier $DB_INSTANCE_ID
# aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
