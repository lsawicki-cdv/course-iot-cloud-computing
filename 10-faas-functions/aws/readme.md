# AWS Lambda - Serverless Computing Exercise

This is the AWS version of the [Azure Functions exercise](../readme.md). You'll build an HTTP-triggered function, test it, and deploy it to AWS. In Part 5 you'll turn a function into a small **AI agent** that answers questions about IoT devices with a model from **Amazon Bedrock**.

| Azure | AWS |
|-------|-----|
| Azure Functions | AWS Lambda |
| Function App (Flex Consumption plan) | Lambda function (one function per deployment package) |
| HTTP trigger (`/api/hello`) | Function URL (`https://<id>.lambda-url.<region>.on.aws/`) |
| Authorization level Anonymous | Function URL auth type `NONE` |
| Function key (`?code=...`) | IAM permission `lambda:InvokeFunction` (`aws lambda invoke`) |
| Azure Functions Core Tools (`func start`) | Running the handler locally with `test_locally.py` |
| `func azure functionapp publish` | `zip` + `aws lambda create-function` / `update-function-code` |
| Timer trigger | EventBridge schedule rule |
| Application settings | Environment variables |
| Application Insights / log stream | CloudWatch Logs (`aws logs tail`) |
| Managed identity / API key for the model | IAM execution role that may call one Bedrock model |
| Azure OpenAI in Foundry (`gpt-5.4-mini`) | Amazon Bedrock (`Amazon Nova 2 Lite`) |
| Chat Completions API with `tools` | Bedrock Converse API with `toolConfig` |
| Resource group | No direct equivalent - resources are deleted one by one |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. AWS Lambda is Free Tier eligible (1 million requests per month). **Amazon Bedrock is not in the Free Tier**: on accounts created after July 2025 it is paid from your Free Tier credits, on older accounts you pay per token - a question to the agent costs a fraction of a cent. Delete all resources at the end of the exercise.

## What is AWS Lambda?

**AWS Lambda** is a serverless compute service: you upload the code of a function, and AWS runs it when an event arrives - an HTTP request, a schedule, a message, a new file. You pay only for the requests and the time your code runs. There are no servers to manage, and Lambda starts more copies of the function automatically when more requests arrive.

### Key concepts

- **Function** - your code with a **handler** (`lambda_function.lambda_handler`): the Python function Lambda calls with the `event` (the input) and the `context`
- **Deployment package** - a `.zip` file with your code. Libraries that aren't part of the Lambda runtime must be in the zip too; `boto3` (the AWS SDK for Python) is already included
- **Execution role** - the IAM role the function runs with. It says what the function may do: write logs, and in Part 5 call one Bedrock model
- **Function URL** - an HTTPS address of the function. With the auth type `NONE` anyone can call it
- **CloudWatch Logs** - everything the function prints or logs, one log group per function (`/aws/lambda/<function-name>`)

## Tested Environments

- AWS CloudShell (Bash)
- Ubuntu 24.04, Python 3.12 (local tests)
- Lambda runtime Python 3.13

## Prerequisites

- An AWS account (see [1-cloud-account/aws](../../1-cloud-account/aws/readme.md))
- Optional: Python 3.10 or higher on your computer, for the local tests

---

## Part 1: Setup Your Development Environment

### Step 1: Open AWS CloudShell

All the commands run in **AWS CloudShell** (the terminal icon in the AWS Console's top bar). It already has the AWS CLI, Python 3, `boto3` and `zip`, and is signed in as you. Check the region in the top-right corner of the Console.

### Step 2: Check the Tools

```bash
aws --version
```
```bash
python3 --version
```

You can also run the local tests on your computer: clone this repository, open the `10-faas-functions/aws` folder, and install `boto3` in a virtual environment (`pip install boto3`). For the agent you then need AWS credentials on your computer (see [1-cloud-account/aws](../../1-cloud-account/aws/readme.md)).

---

## Part 2: Create Your First Lambda Function

### Step 3: Download the Code

In CloudShell (the same in Bash and PowerShell; start PowerShell by typing `pwsh`):
```bash
curl -o lambda_function.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/aws/lambda_function.py
```
```bash
curl -o test_locally.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/aws/test_locally.py
```

### Step 4: Understanding the Function Code

Open `lambda_function.py` (`cat lambda_function.py`):

```python
def lambda_handler(event, context):
    logger.info('Python HTTP trigger function processed a request.')

    # Query string parameter, for example ?name=Student
    name = (event.get('queryStringParameters') or {}).get('name')
    if not name and event.get('body'):
        body = event['body']
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body).decode('utf-8')
        try:
            name = json.loads(body).get('name')
        except (ValueError, AttributeError):
            pass

    if name:
        message = f"Hello, {name}. This HTTP-triggered function executed successfully."
    else:
        message = ("This HTTP-triggered function executed successfully. Pass a name in the query string "
                   "or in the request body for a personalized response.")
    return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": message}
```

**Key concepts:**
- `lambda_handler(event, context)` - the function Lambda calls. For a function URL, `event` describes the HTTP request
- `event['queryStringParameters']` - the query parameters (`?name=Student`)
- `event['body']` - the request body (the JSON of a POST request), sometimes Base64 encoded
- The return value - the HTTP status code, the headers and the body of the response

It does the same as `function_app.py` in the Azure version.

### Step 5: Test the Function Locally

`test_locally.py` calls the handler with an event like the one a function URL sends (the same in Bash and PowerShell):
```bash
python3 test_locally.py hello Student
```

You should see:
```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "text/plain"
  },
  "body": "Hello, Student. This HTTP-triggered function executed successfully."
}
```

---

## Part 3: Deploy the Function to AWS

### Step 6: Create the Lambda Function

In CloudShell:

**Option A: Using Bash (recommended)**

Set environment variables:
```bash
REGION="eu-west-2"  # Change to another region if needed
```
```bash
FUNCTION_NAME="my-hello-function"
```
```bash
RUNTIME="python3.13"
```

Create the execution role of the function. The trust policy lets Lambda use the role, and `AWSLambdaBasicExecutionRole` allows writing logs:
```bash
cat > lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
EOF
```
```bash
ROLE_ARN=$(aws iam create-role \
  --role-name ${FUNCTION_NAME}-role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --query Role.Arn \
  --output text)
```
```bash
aws iam attach-role-policy \
  --role-name ${FUNCTION_NAME}-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Package the code and create the function. If it fails with `The role defined for the function cannot be assumed by Lambda`, the new role isn't ready yet: wait 10 seconds and try again:
```bash
zip hello.zip lambda_function.py
```
```bash
aws lambda create-function \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --runtime $RUNTIME \
  --handler lambda_function.lambda_handler \
  --role $ROLE_ARN \
  --zip-file fileb://hello.zip
```
```bash
aws lambda wait function-active-v2 --region $REGION --function-name $FUNCTION_NAME
```

**Option B: Using PowerShell**

Set environment variables (PowerShell syntax):
```powershell
$REGION="eu-west-2"  # Change to another region if needed
```
```powershell
$FUNCTION_NAME="my-hello-function"
```
```powershell
$RUNTIME="python3.13"
```

Create the execution role of the function. The trust policy lets Lambda use the role, and `AWSLambdaBasicExecutionRole` allows writing logs:
```powershell
@'
{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}
'@ | Set-Content lambda-trust-policy.json
```
```powershell
$ROLE_ARN=$(aws iam create-role `
  --role-name "$FUNCTION_NAME-role" `
  --assume-role-policy-document file://lambda-trust-policy.json `
  --query Role.Arn `
  --output text)
```
```powershell
aws iam attach-role-policy `
  --role-name "$FUNCTION_NAME-role" `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Package the code and create the function. If it fails with `The role defined for the function cannot be assumed by Lambda`, the new role isn't ready yet: wait 10 seconds and try again:
```powershell
zip hello.zip lambda_function.py
```
```powershell
aws lambda create-function `
  --region $REGION `
  --function-name $FUNCTION_NAME `
  --runtime $RUNTIME `
  --handler lambda_function.lambda_handler `
  --role $ROLE_ARN `
  --zip-file fileb://hello.zip
```
```powershell
aws lambda wait function-active-v2 --region $REGION --function-name $FUNCTION_NAME
```

### Step 7: Create a Function URL

A function URL gives the function an HTTPS address. With `--auth-type NONE` anyone can call it, like an Azure function with the authorization level Anonymous. Two permissions allow the public calls: one for the URL and one for running the function through it (without the second one the URL answers `403 Forbidden`).

**Option A: Using Bash (recommended)**
```bash
FUNCTION_URL=$(aws lambda create-function-url-config \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --auth-type NONE \
  --query FunctionUrl \
  --output text)
```
```bash
aws lambda add-permission \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --statement-id public-url \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE
```
```bash
aws lambda add-permission \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --statement-id public-url-invoke \
  --action lambda:InvokeFunction \
  --principal "*" \
  --invoked-via-function-url
```
```bash
echo $FUNCTION_URL
```

**Option B: Using PowerShell**
```powershell
$FUNCTION_URL=$(aws lambda create-function-url-config `
  --region $REGION `
  --function-name $FUNCTION_NAME `
  --auth-type NONE `
  --query FunctionUrl `
  --output text)
```
```powershell
aws lambda add-permission `
  --region $REGION `
  --function-name $FUNCTION_NAME `
  --statement-id public-url `
  --action lambda:InvokeFunctionUrl `
  --principal "*" `
  --function-url-auth-type NONE
```
```powershell
aws lambda add-permission `
  --region $REGION `
  --function-name $FUNCTION_NAME `
  --statement-id public-url-invoke `
  --action lambda:InvokeFunction `
  --principal "*" `
  --invoked-via-function-url
```
```powershell
$FUNCTION_URL
```

### Step 8: Test Your Deployed Function

Open the function URL in the browser with `?name=YourName` at the end, or use `curl` (the same in Bash and PowerShell):
```bash
curl "${FUNCTION_URL}?name=Student"
```
```bash
curl -X POST $FUNCTION_URL -H "Content-Type: application/json" -d '{"name":"Student"}'
```

You should see the same response as in the local test:
```
Hello, Student. This HTTP-triggered function executed successfully.
```

### Step 9: Monitor Your Function

Show the logs of the last 10 minutes (the same in Bash and PowerShell):
```bash
aws logs tail /aws/lambda/$FUNCTION_NAME --region $REGION --since 10m
```

Every request shows the `logger.info` message and a `REPORT` line with the duration, the billed duration and the memory used.

In the AWS Console: Lambda → Functions → `my-hello-function` → **Monitor**: the number of invocations, the duration and the errors; "View CloudWatch logs" opens the log group.

---

## Part 4: Enhance Your Function (Optional)

### Step 10: Run the Function on a Schedule

The AWS counterpart of a timer trigger is an **EventBridge rule** with a schedule. This one calls the function every minute.

**Option A: Using Bash (recommended)**
```bash
FUNCTION_ARN=$(aws lambda get-function --region $REGION --function-name $FUNCTION_NAME --query Configuration.FunctionArn --output text)
```
```bash
RULE_ARN=$(aws events put-rule \
  --region $REGION \
  --name ${FUNCTION_NAME}-every-minute \
  --schedule-expression "rate(1 minute)" \
  --query RuleArn \
  --output text)
```
```bash
aws lambda add-permission \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --statement-id every-minute \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn $RULE_ARN
```
```bash
aws events put-targets --region $REGION --rule ${FUNCTION_NAME}-every-minute --targets "Id=1,Arn=$FUNCTION_ARN"
```

**Option B: Using PowerShell**
```powershell
$FUNCTION_ARN=$(aws lambda get-function --region $REGION --function-name $FUNCTION_NAME --query Configuration.FunctionArn --output text)
```
```powershell
$RULE_ARN=$(aws events put-rule `
  --region $REGION `
  --name "$FUNCTION_NAME-every-minute" `
  --schedule-expression "rate(1 minute)" `
  --query RuleArn `
  --output text)
```
```powershell
aws lambda add-permission `
  --region $REGION `
  --function-name $FUNCTION_NAME `
  --statement-id every-minute `
  --action lambda:InvokeFunction `
  --principal events.amazonaws.com `
  --source-arn $RULE_ARN
```
```powershell
aws events put-targets --region $REGION --rule "$FUNCTION_NAME-every-minute" --targets "Id=1,Arn=$FUNCTION_ARN"
```

After two or three minutes, the logs (Step 9) show a new request every minute. Stop the schedule when you've seen it (the same in Bash and PowerShell; in PowerShell write `"$FUNCTION_NAME-every-minute"`):
```bash
aws events disable-rule --region $REGION --name ${FUNCTION_NAME}-every-minute
```

### Step 11: Add Environment Variables

The AWS counterpart of application settings are the function's **environment variables** (the same in Bash and PowerShell):
```bash
aws lambda update-function-configuration --region $REGION --function-name $FUNCTION_NAME --environment "Variables={GREETING_MESSAGE=Welcome}"
```

**Update your function to use it:** replace the content of `lambda_function.py` (`nano lambda_function.py`):

```python
import os


def lambda_handler(event, context):
    greeting = os.environ.get('GREETING_MESSAGE', 'Hello')
    name = (event.get('queryStringParameters') or {}).get('name')

    if name:
        message = f"{greeting}, {name}!"
    else:
        message = f"{greeting}! Pass a name parameter."
    return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": message}
```

Deploy the new code and test it (the same in Bash and PowerShell; in PowerShell use `Remove-Item hello.zip` instead of `rm hello.zip`):
```bash
rm hello.zip && zip hello.zip lambda_function.py
```
```bash
aws lambda update-function-code --region $REGION --function-name $FUNCTION_NAME --zip-file fileb://hello.zip
```
```bash
curl "${FUNCTION_URL}?name=Student"
```

You should see `Welcome, Student!`.

---

## Part 5: Build an AI Agent with Amazon Bedrock

An **AI agent** is a program in which a language model decides which actions to take. Here the model answers questions about IoT devices, such as "Is any device too hot?". It doesn't know the readings itself, so it asks your code to run **tools** - ordinary Python functions - and uses their results in the answer.

The model comes from **Amazon Bedrock**: **Amazon Nova 2 Lite**, through the `eu.amazon.nova-2-lite-v1:0` inference profile (an inference profile sends the requests to the model in one of the EU regions).

**The agent loop** (in `ask_agent()` in `agent_function.py`):
1. Send the question and the list of tools to the model (the Bedrock **Converse API**)
2. If the model asks for a tool (`stopReason` is `tool_use`), run it and send the result back
3. Repeat until the model answers with text - or stop after 5 model calls (`MAX_STEPS`), so a confused model can't run (and cost) forever

**The files:**
- `../sensor_tools.py` - the tools: `list_devices` and `get_sensor_reading` return simulated data for three devices, with a description and a JSON schema of the input for the model. `run_tool()` checks the input the model sends, because the model's output is untrusted. The Azure version of this exercise uses the same file
- `agent_function.py` - the Lambda function that runs the loop with `boto3`

The agent gets **no function URL**: it's called with `aws lambda invoke`, which needs your AWS credentials, so nobody else can spend your credits.

### Step 12: Check the Model

In CloudShell, check that the inference profile is available in your region (the same in Bash and PowerShell):
```bash
aws bedrock list-inference-profiles --region $REGION --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'nova-2-lite')].inferenceProfileId" --output text
```

Ask the model a first question directly:

**Bash:**
```bash
aws bedrock-runtime converse \
  --region $REGION \
  --model-id eu.amazon.nova-2-lite-v1:0 \
  --messages '[{"role": "user", "content": [{"text": "Explain in one sentence what an IoT device is."}]}]' \
  --inference-config '{"maxTokens": 200}' \
  --query "output.message.content[0].text" \
  --output text
```

**PowerShell:**
```powershell
aws bedrock-runtime converse `
  --region $REGION `
  --model-id eu.amazon.nova-2-lite-v1:0 `
  --messages '[{"role": "user", "content": [{"text": "Explain in one sentence what an IoT device is."}]}]' `
  --inference-config '{"maxTokens": 200}' `
  --query "output.message.content[0].text" `
  --output text
```

Amazon models (Nova) work without any extra step. If you get an `AccessDeniedException` about model access, open Amazon Bedrock → **Model catalog** in the Console, select the model and follow the instructions there.

### Step 13: Look at the Agent Code

Download the agent and the shared tools (the same in Bash and PowerShell):
```bash
curl -o agent_function.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/aws/agent_function.py
```
```bash
curl -o sensor_tools.py https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/10-faas-functions/sensor_tools.py
```

Open `agent_function.py` and find `ask_agent()`:
- `boto3.client("bedrock-runtime")` - the client for calling models
- `TOOL_CONFIG` - the tools from `sensor_tools.py` in the format of the Converse API (`toolSpec` with an `inputSchema`)
- `bedrock.converse(..., toolConfig=TOOL_CONFIG, inferenceConfig={"maxTokens": 500, ...})` - one model call; always limit the length of the answer
- `block["toolUse"]` - a tool the model wants to run. Each result goes back as a `toolResult` with the same `toolUseId`

The answer of the function contains the model's `answer` and the `steps` - every tool the model called, with its input and result - so you can see how the agent worked.

### Step 14: Test the Agent Locally

Run the agent in CloudShell, with your own credentials (the same in Bash and PowerShell):
```bash
python3 test_locally.py agent "Is any device too hot?"
```

You should get an answer like this (the readings are random, so the numbers differ):
```json
{
  "answer": "Yes, device-02 in the Greenhouse is too hot. Its temperature is 32.6°C, which exceeds the maximum allowed temperature of 30°C.",
  "steps": [
    {"tool": "list_devices", "input": {}, "result": {"devices": [...]}},
    {"tool": "get_sensor_reading", "input": {"device_id": "device-01"}, "result": {...}},
    {"tool": "get_sensor_reading", "input": {"device_id": "device-02"}, "result": {...}},
    {"tool": "get_sensor_reading", "input": {"device_id": "device-03"}, "result": {...}}
  ]
}
```

Look at the `steps`: the model first listed the devices, then asked for the reading of each one, and only then answered. Try other questions, for example `"What is the humidity in the warehouse?"` or `"Is device-99 OK?"` (an unknown device - watch how the model reacts to the tool's error message).

### Step 15: Deploy the Agent to AWS

The agent's execution role may write logs and call **only** the Nova 2 Lite model: the inference profile in your region, and the model in the EU regions the profile sends the requests to.

**Option A: Using Bash (recommended)**

Set environment variables:
```bash
AGENT_FUNCTION_NAME="iot-agent"
```
```bash
MODEL_ID="eu.amazon.nova-2-lite-v1:0"
```
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

Create the execution role:
```bash
ROLE_ARN=$(aws iam create-role \
  --role-name ${AGENT_FUNCTION_NAME}-role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --query Role.Arn \
  --output text)
```
```bash
aws iam attach-role-policy \
  --role-name ${AGENT_FUNCTION_NAME}-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```bash
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
```
```bash
aws iam put-role-policy \
  --role-name ${AGENT_FUNCTION_NAME}-role \
  --policy-name invoke-model \
  --policy-document file://bedrock-policy.json
```

Package the agent together with the shared tools and create the function. A model call takes a few seconds, so the timeout is 60 seconds instead of the default 3. If it fails with `The role defined for the function cannot be assumed by Lambda`, wait 10 seconds and try again:
```bash
zip agent.zip agent_function.py sensor_tools.py
```
```bash
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
```
```bash
aws lambda wait function-active-v2 --region $REGION --function-name $AGENT_FUNCTION_NAME
```

**Option B: Using PowerShell**

Set environment variables (PowerShell syntax):
```powershell
$AGENT_FUNCTION_NAME="iot-agent"
```
```powershell
$MODEL_ID="eu.amazon.nova-2-lite-v1:0"
```
```powershell
$ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

Create the execution role:
```powershell
$ROLE_ARN=$(aws iam create-role `
  --role-name "$AGENT_FUNCTION_NAME-role" `
  --assume-role-policy-document file://lambda-trust-policy.json `
  --query Role.Arn `
  --output text)
```
```powershell
aws iam attach-role-policy `
  --role-name "$AGENT_FUNCTION_NAME-role" `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```powershell
$BASE_MODEL_ID=$MODEL_ID.Substring($MODEL_ID.IndexOf('.') + 1)
@"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock:InvokeModel",
    "Resource": [
      "arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:inference-profile/$MODEL_ID",
      "arn:aws:bedrock:*::foundation-model/$BASE_MODEL_ID"
    ]
  }]
}
"@ | Set-Content bedrock-policy.json
```
```powershell
aws iam put-role-policy `
  --role-name "$AGENT_FUNCTION_NAME-role" `
  --policy-name invoke-model `
  --policy-document file://bedrock-policy.json
```

Package the agent together with the shared tools and create the function. A model call takes a few seconds, so the timeout is 60 seconds instead of the default 3. If it fails with `The role defined for the function cannot be assumed by Lambda`, wait 10 seconds and try again:
```powershell
zip agent.zip agent_function.py sensor_tools.py
```
```powershell
aws lambda create-function `
  --region $REGION `
  --function-name $AGENT_FUNCTION_NAME `
  --runtime $RUNTIME `
  --handler agent_function.lambda_handler `
  --role $ROLE_ARN `
  --zip-file fileb://agent.zip `
  --timeout 60 `
  --memory-size 256 `
  --environment "Variables={MODEL_ID=$MODEL_ID}"
```
```powershell
aws lambda wait function-active-v2 --region $REGION --function-name $AGENT_FUNCTION_NAME
```

### Step 16: Ask the Deployed Agent

`aws lambda invoke` sends the question as the `event` and saves the answer to `answer.json` (the same in Bash and PowerShell):
```bash
aws lambda invoke \
  --region $REGION \
  --function-name $AGENT_FUNCTION_NAME \
  --cli-binary-format raw-in-base64-out \
  --payload '{"question": "Is any device too hot?"}' \
  answer.json
```
In PowerShell, write the command in one line (or end the lines with `` ` ``). Then show the answer:
```bash
cat answer.json
```

The logs show the question, every tool call and the answer (the same in Bash and PowerShell):
```bash
aws logs tail /aws/lambda/$AGENT_FUNCTION_NAME --region $REGION --since 10m
```

### Step 17: Explore and Extend the Agent

1. In the AWS Console, open CloudWatch → **Metrics** → **Bedrock** → "By Model Id": the invocations and the input and output tokens of your agent
2. Change `SYSTEM_PROMPT` in `sensor_tools.py`, for example tell the model to answer in Polish, test it locally (Step 14), then deploy the new code: `zip agent.zip agent_function.py sensor_tools.py` and `aws lambda update-function-code --region $REGION --function-name $AGENT_FUNCTION_NAME --zip-file fileb://agent.zip`
3. Add a third tool: write a function in `sensor_tools.py` (for example `get_devices_by_location(location)`), add its definition to `TOOLS` and a branch in `run_tool()`. Then ask a question that needs it - the model finds the new tool from its description

---

## Cleanup

**Don't forget to delete your resources!** Run these commands in **AWS CloudShell**, in the session where you set the variables (the same in Bash and PowerShell; in PowerShell write `"$FUNCTION_NAME-every-minute"`, `"$FUNCTION_NAME-role"` and `"$AGENT_FUNCTION_NAME-role"`).

Delete the schedule from Step 10 (skip it if you didn't do Part 4):
```bash
aws events remove-targets --region $REGION --rule ${FUNCTION_NAME}-every-minute --ids 1
```
```bash
aws events delete-rule --region $REGION --name ${FUNCTION_NAME}-every-minute
```

Delete the functions (this also deletes the function URL):
```bash
aws lambda delete-function --region $REGION --function-name $FUNCTION_NAME
```
```bash
aws lambda delete-function --region $REGION --function-name $AGENT_FUNCTION_NAME
```

Delete the execution roles:
```bash
aws iam detach-role-policy --role-name ${FUNCTION_NAME}-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```bash
aws iam delete-role --role-name ${FUNCTION_NAME}-role
```
```bash
aws iam detach-role-policy --role-name ${AGENT_FUNCTION_NAME}-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```
```bash
aws iam delete-role-policy --role-name ${AGENT_FUNCTION_NAME}-role --policy-name invoke-model
```
```bash
aws iam delete-role --role-name ${AGENT_FUNCTION_NAME}-role
```

Delete the log groups (Lambda doesn't delete them with the function):
```bash
aws logs delete-log-group --region $REGION --log-group-name /aws/lambda/$FUNCTION_NAME
```
```bash
aws logs delete-log-group --region $REGION --log-group-name /aws/lambda/$AGENT_FUNCTION_NAME
```

---

## Troubleshooting

- **`The role defined for the function cannot be assumed by Lambda`** - the new IAM role isn't ready yet. Wait 10 seconds and run `create-function` again
- **The function URL answers `403 Forbidden`** - one of the two `add-permission` commands of Step 7 is missing
- **`Task timed out after 3.00 seconds`** - the function's timeout is too short; the agent needs `--timeout 60`
- **`AccessDeniedException` when the agent calls the model** - check the region and the model in `bedrock-policy.json`; IAM changes can take a few seconds to apply
- **`ValidationException` about the model ID** - the inference profile isn't available in your region; list the profiles (Step 12) and use one that is, both in `MODEL_ID` and in the policy

## Summary and Learning Outcomes

You learned:

✅ **Serverless Concepts**: Function-as-a-Service (FaaS) and event-driven computing
✅ **AWS Lambda**: Handlers, events, deployment packages and execution roles
✅ **Function URLs**: Calling a function over HTTPS
✅ **Schedules and configuration**: EventBridge rules and environment variables
✅ **Monitoring**: CloudWatch Logs and metrics
✅ **AI Agents**: A tool-use loop with the Amazon Bedrock Converse API, with an execution role that may call only one model

## Additional Resources

- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- [Lambda function URLs](https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html)
- [Amazon Bedrock Converse API - tool use](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html)
- [Amazon Bedrock inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)
- [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
