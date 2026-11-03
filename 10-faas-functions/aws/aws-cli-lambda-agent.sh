#!/bin/bash

# Variables
REGION="eu-west-2"
FUNCTION_NAME="my-hello-function"
AGENT_FUNCTION_NAME="iot-agent"
MODEL_ID="eu.amazon.nova-2-lite-v1:0"
RUNTIME="python3.13"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Download the function code
curl -o lambda_function.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/aws/lambda_function.py
curl -o agent_function.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/aws/agent_function.py
curl -o sensor_tools.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/sensor_tools.py

# --- Part 3: the hello function with a public function URL ---

# Create the execution role of the function (it may write logs to CloudWatch)
cat > lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
EOF

ROLE_ARN=$(aws iam create-role \
  --role-name ${FUNCTION_NAME}-role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --query Role.Arn \
  --output text)

aws iam attach-role-policy \
  --role-name ${FUNCTION_NAME}-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Package and create the function (wait 10 seconds and retry if the role isn't ready yet)
zip hello.zip lambda_function.py

aws lambda create-function \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --runtime $RUNTIME \
  --handler lambda_function.lambda_handler \
  --role $ROLE_ARN \
  --zip-file fileb://hello.zip

aws lambda wait function-active-v2 --region $REGION --function-name $FUNCTION_NAME

# Create a public function URL (no authentication) and allow anyone to call it
FUNCTION_URL=$(aws lambda create-function-url-config \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --auth-type NONE \
  --query FunctionUrl \
  --output text)

aws lambda add-permission \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --statement-id public-url \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE

aws lambda add-permission \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --statement-id public-url-invoke \
  --action lambda:InvokeFunction \
  --principal "*" \
  --invoked-via-function-url

curl "${FUNCTION_URL}?name=Student"

# Show the function's logs
aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --since 10m

# --- Part 5: the AI agent on Amazon Bedrock ---

# Create the execution role of the agent: logs, and calling only the chosen model
ROLE_ARN=$(aws iam create-role \
  --role-name ${AGENT_FUNCTION_NAME}-role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --query Role.Arn \
  --output text)

aws iam attach-role-policy \
  --role-name ${AGENT_FUNCTION_NAME}-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

cat > bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock:InvokeModel",
    "Resource": [
      "arn:aws:bedrock:$REGION:$ACCOUNT_ID:inference-profile/$MODEL_ID",
      "arn:aws:bedrock:*::foundation-model/${MODEL_ID#*.}"
    ]
  }]
}
EOF

aws iam put-role-policy \
  --role-name ${AGENT_FUNCTION_NAME}-role \
  --policy-name invoke-model \
  --policy-document file://bedrock-policy.json

# Package the agent together with the shared tools and create the function
zip agent.zip agent_function.py sensor_tools.py

aws lambda create-function \
  --region $REGION \
  --function-name $AGENT_FUNCTION_NAME \
  --runtime $RUNTIME \
  --handler agent_function.lambda_handler \
  --role $ROLE_ARN \
  --zip-file fileb://agent.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment "Variables={MODEL_ID=$MODEL_ID}"

aws lambda wait function-active-v2 --region $REGION --function-name $AGENT_FUNCTION_NAME

# Ask the agent a question
aws lambda invoke \
  --region $REGION \
  --function-name $AGENT_FUNCTION_NAME \
  --cli-binary-format raw-in-base64-out \
  --payload '{"question": "Is any device too hot?"}' \
  answer.json

cat answer.json

# Delete all resources
# aws lambda delete-function --region $REGION --function-name $FUNCTION_NAME
# aws lambda delete-function --region $REGION --function-name $AGENT_FUNCTION_NAME
# aws iam detach-role-policy --role-name ${FUNCTION_NAME}-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
# aws iam delete-role --role-name ${FUNCTION_NAME}-role
# aws iam detach-role-policy --role-name ${AGENT_FUNCTION_NAME}-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
# aws iam delete-role-policy --role-name ${AGENT_FUNCTION_NAME}-role --policy-name invoke-model
# aws iam delete-role --role-name ${AGENT_FUNCTION_NAME}-role
# aws logs delete-log-group --region $REGION --log-group-name /aws/lambda/$FUNCTION_NAME
# aws logs delete-log-group --region $REGION --log-group-name /aws/lambda/$AGENT_FUNCTION_NAME
