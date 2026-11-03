#!/bin/bash

# Variables
REGION="eu-west-2"
THING_NAME="my-device-01"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create a thing (the device identity)
aws iot create-thing --region $REGION --thing-name $THING_NAME

# Create the device certificate and private key
CERTIFICATE_ARN=$(aws iot create-keys-and-certificate \
  --region $REGION \
  --set-as-active \
  --certificate-pem-outfile device.pem.crt \
  --private-key-outfile private.pem.key \
  --query certificateArn \
  --output text)

# Create a policy that allows the device to connect and publish to its own topics
cat > device-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:topic/devices/$THING_NAME/*"}
  ]
}
EOF

aws iot create-policy \
  --region $REGION \
  --policy-name ${THING_NAME}-policy \
  --policy-document file://device-policy.json

# Attach the policy to the certificate and the certificate to the thing
aws iot attach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN

aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN

# Get the IoT Core endpoint (the MQTT broker hostname)
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text

# !!! Download device.pem.crt and private.pem.key from CloudShell (Actions -> Download file)

# Delete the IoT Core resources
# CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
# aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
# aws iot detach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
# aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
# aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
# aws iot delete-thing --region $REGION --thing-name $THING_NAME
# aws iot delete-policy --region $REGION --policy-name ${THING_NAME}-policy
