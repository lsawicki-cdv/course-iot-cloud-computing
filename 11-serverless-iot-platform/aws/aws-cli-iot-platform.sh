#!/bin/bash

# Variables
REGION="eu-west-2"
THING_NAME="my-iot-device-01"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Register the device: thing, certificate and IoT policy
aws iot create-thing --region $REGION --thing-name $THING_NAME

CERTIFICATE_ARN=$(aws iot create-keys-and-certificate \
  --region $REGION \
  --set-as-active \
  --certificate-pem-outfile device.pem.crt \
  --private-key-outfile private.pem.key \
  --query certificateArn \
  --output text)

cat > device-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "iot:Connect", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:client/$THING_NAME"},
    {"Effect": "Allow", "Action": "iot:Publish", "Resource": "arn:aws:iot:$REGION:$ACCOUNT_ID:topic/devices/$THING_NAME/*"}
  ]
}
EOF
aws iot create-policy --region $REGION --policy-name ${THING_NAME}-policy --policy-document file://device-policy.json
aws iot attach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
aws iot attach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN

# Get the IoT Core endpoint (the MQTT broker hostname)
aws iot describe-endpoint --region $REGION --endpoint-type iot:Data-ATS --query endpointAddress --output text

# TODO: Download device.pem.crt and private.pem.key, update and run the AWS simulator from 6-paas-iot-mqtt/aws

# Create the DynamoDB tables
aws dynamodb create-table --region $REGION --table-name iot-data \
  --attribute-definitions AttributeName=deviceid,AttributeType=S AttributeName=timestamp,AttributeType=N \
  --key-schema AttributeName=deviceid,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

for TABLE in house-data room-data; do
  aws dynamodb create-table --region $REGION --table-name $TABLE \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
done

for TABLE in iot-data house-data room-data; do
  aws dynamodb wait table-exists --region $REGION --table-name $TABLE
done

# Create the role of the IoT rule (may write only to the iot-data table)
cat > iot-rule-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "iot.amazonaws.com"}, "Action": "sts:AssumeRole",
                 "Condition": {"StringEquals": {"aws:SourceAccount": "$ACCOUNT_ID"}}}]
}
EOF
IOT_RULE_ROLE_ARN=$(aws iam create-role --role-name iot-data-to-dynamodb-role \
  --assume-role-policy-document file://iot-rule-trust-policy.json --query Role.Arn --output text)

cat > iot-rule-dynamodb-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/iot-data"}]
}
EOF
aws iam put-role-policy --role-name iot-data-to-dynamodb-role --policy-name write-iot-data --policy-document file://iot-rule-dynamodb-policy.json

# Create the IoT rule (instead of Stream Analytics): select the readings and write them to DynamoDB
cat > iot-rule.json <<EOF
{
  "sql": "SELECT temperature, humidity, pressure, timestamp, device_id AS deviceid FROM 'devices/+/messages/events/'",
  "awsIotSqlVersion": "2016-03-23",
  "ruleDisabled": false,
  "actions": [{"dynamoDBv2": {"putItem": {"tableName": "iot-data"}, "roleArn": "$IOT_RULE_ROLE_ARN"}}]
}
EOF
sleep 10  # Wait until the new role is ready
aws iot create-topic-rule --region $REGION --rule-name iot_data_to_dynamodb --topic-rule-payload file://iot-rule.json

# Create the role of the Lambda functions (logs + the three tables)
API_KEY=$(openssl rand -hex 16)

cat > lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
EOF
LAMBDA_ROLE_ARN=$(aws iam create-role --role-name iot-platform-api-role \
  --assume-role-policy-document file://lambda-trust-policy.json --query Role.Arn --output text)
aws iam attach-role-policy --role-name iot-platform-api-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

cat > lambda-dynamodb-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Action": ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem"],
                 "Resource": ["arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/iot-data",
                              "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/house-data",
                              "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/room-data"]}]
}
EOF
aws iam put-role-policy --role-name iot-platform-api-role --policy-name read-write-iot-platform-tables \
  --policy-document file://lambda-dynamodb-policy.json

# Create the three functions from one zip file (run from the 11-serverless-iot-platform/aws directory)
cd iot-lambda-api && zip ../iot-lambda-api.zip *.py && cd ..
sleep 10  # Wait until the new role is ready
for FUNCTION in device house rooms; do
  aws lambda create-function --region $REGION --function-name iot-platform-$FUNCTION \
    --runtime python3.13 --handler $FUNCTION.lambda_handler --role $LAMBDA_ROLE_ARN \
    --zip-file fileb://iot-lambda-api.zip --environment "Variables={API_KEY=$API_KEY}"
done

# Create the HTTP API with GET and POST routes for each function
API_ID=$(aws apigatewayv2 create-api --region $REGION --name iot-platform-api --protocol-type HTTP \
  --cors-configuration "AllowOrigins=*,AllowMethods=GET,POST,OPTIONS,AllowHeaders=content-type" \
  --query ApiId --output text)

for FUNCTION in device house rooms; do
  INTEGRATION_ID=$(aws apigatewayv2 create-integration --region $REGION --api-id $API_ID \
    --integration-type AWS_PROXY \
    --integration-uri arn:aws:lambda:$REGION:$ACCOUNT_ID:function:iot-platform-$FUNCTION \
    --payload-format-version 2.0 --query IntegrationId --output text)
  aws apigatewayv2 create-route --region $REGION --api-id $API_ID --route-key "GET /api/$FUNCTION" --target integrations/$INTEGRATION_ID
  aws apigatewayv2 create-route --region $REGION --api-id $API_ID --route-key "POST /api/$FUNCTION" --target integrations/$INTEGRATION_ID
  aws lambda add-permission --region $REGION --function-name iot-platform-$FUNCTION \
    --statement-id allow-api-gateway --action lambda:InvokeFunction --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*/api/$FUNCTION"
done

aws apigatewayv2 create-stage --region $REGION --api-id $API_ID --stage-name '$default' --auto-deploy

echo "API URL: https://$API_ID.execute-api.$REGION.amazonaws.com"
echo "API key: $API_KEY"

# Test the API
curl "https://$API_ID.execute-api.$REGION.amazonaws.com/api/device?device_id=$THING_NAME&code=$API_KEY"

# Delete all resources
# aws apigatewayv2 delete-api --region $REGION --api-id $API_ID
# for FUNCTION in device house rooms; do
#   aws lambda delete-function --region $REGION --function-name iot-platform-$FUNCTION
#   aws logs delete-log-group --region $REGION --log-group-name /aws/lambda/iot-platform-$FUNCTION
# done
# aws iam delete-role-policy --role-name iot-platform-api-role --policy-name read-write-iot-platform-tables
# aws iam detach-role-policy --role-name iot-platform-api-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
# aws iam delete-role --role-name iot-platform-api-role
# aws iot delete-topic-rule --region $REGION --rule-name iot_data_to_dynamodb
# aws iam delete-role-policy --role-name iot-data-to-dynamodb-role --policy-name write-iot-data
# aws iam delete-role --role-name iot-data-to-dynamodb-role
# for TABLE in iot-data house-data room-data; do aws dynamodb delete-table --region $REGION --table-name $TABLE; done
# CERTIFICATE_ID=${CERTIFICATE_ARN##*/}
# aws iot detach-thing-principal --region $REGION --thing-name $THING_NAME --principal $CERTIFICATE_ARN
# aws iot detach-policy --region $REGION --policy-name ${THING_NAME}-policy --target $CERTIFICATE_ARN
# aws iot update-certificate --region $REGION --certificate-id $CERTIFICATE_ID --new-status INACTIVE
# aws iot delete-certificate --region $REGION --certificate-id $CERTIFICATE_ID
# aws iot delete-thing --region $REGION --thing-name $THING_NAME
# aws iot delete-policy --region $REGION --policy-name ${THING_NAME}-policy
