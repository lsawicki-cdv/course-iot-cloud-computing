# AWS Lambda Deployment with CloudFormation

This is the AWS version of the [Bicep exercise](../readme.md). You'll learn Infrastructure as Code (IaC) using **AWS CloudFormation**, AWS's own service for deploying resources from templates. You'll deploy a complete serverless function environment: the function, its HTTPS address, its permissions and its logs.

| Azure | AWS |
|-------|-----|
| Bicep (`main.bicep`) | CloudFormation template (`template.yaml`) |
| ARM templates (JSON) | CloudFormation templates can be JSON too; YAML is easier to read |
| Resource group + deployment (`az deployment group create`) | Stack (`aws cloudformation deploy`) - deleting the stack deletes all its resources |
| `param` (with `@allowed`) | `Parameters` (with `AllowedValues`) |
| `var` | No direct equivalent - `!Sub` / `!Ref` / `!GetAtt` inside the properties |
| `uniqueString(resourceGroup().id)` | `${AWS::StackName}` in names (Lambda names are unique per account and region) |
| `output` | `Outputs` |
| What-if (`az deployment group what-if`) | Change set (`aws cloudformation deploy --no-execute-changeset`) |
| `az bicep build` | `aws cloudformation validate-template`, `cfn-lint` |
| Bicep modules | Nested stacks (`AWS::CloudFormation::Stack`) |
| Function App (Flex Consumption plan) + Storage Account | Lambda function (`AWS::Lambda::Function`) - Lambda stores the code itself |
| Function App URL (`https://<app>.azurewebsites.net/api/...`) | Function URL (`AWS::Lambda::Url`, `https://<id>.lambda-url.<region>.on.aws/`) |
| Managed identity | IAM execution role (`AWS::IAM::Role`) |
| Application Insights + Log Analytics workspace | CloudWatch Logs log group (`AWS::Logs::LogGroup`) |
| `func azure functionapp publish` | `zip` + `aws lambda update-function-code` |
| UK South (`uksouth`) | Europe (London) (`eu-west-2`) |

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. If your account is limited to one region (for example a new AWS account with a selected Region), use that region instead. Everything in this exercise is Free Tier eligible: CloudFormation costs nothing for AWS resources, AWS Lambda includes 1 million requests per month, and CloudWatch Logs includes 5 GB of logs per month. Delete the stack at the end of the exercise anyway.

## What is AWS CloudFormation?

**AWS CloudFormation** is the IaC service of AWS. You describe resources in a **template** (YAML or JSON), and CloudFormation creates them as one unit called a **stack**. It's:
- **AWS-native** - designed specifically for AWS (unlike Terraform which is multi-cloud), like Bicep is for Azure
- **A managed service** - CloudFormation itself runs the deployment, keeps track of the resources and rolls back when something fails; there is no local state file
- **Fully supported by AWS** - new AWS features usually come to CloudFormation first
- **The base of other tools** - AWS CDK and AWS SAM generate CloudFormation templates, like Bicep generates ARM templates

### CloudFormation vs Other IaC Tools

| Feature | CloudFormation | Bicep | Terraform |
|---------|----------------|-------|-----------|
| Syntax | YAML or JSON | Clean, concise | HCL (HashiCorp) |
| Cloud Support | AWS only | Azure only | Multi-cloud |
| State | Kept by the service (the stack) | Kept by Azure (the resources) | State file |
| Rollback on failure | Automatic | No | No |

## Architecture Overview

This CloudFormation template deploys the following resources:

```
Stack (cloud-computing-faas)
  ├── IAM Role (execution role: the function may write its logs)
  ├── Log Group (/aws/lambda/cloud-computing-faas-function, 7 days retention)
  ├── Lambda Function (Node.js 24 runtime)
  ├── Function URL (public HTTPS address of the function)
  └── 2 Lambda Permissions (allow anyone to call the function URL)
```

Compared with the Azure version, there is no storage account and no hosting plan: Lambda keeps the code of the function itself, and you pay only per request and per millisecond the code runs.

### What You'll Learn

- How to write and understand CloudFormation templates
- How to deploy AWS resources using Infrastructure as Code
- AWS Lambda architecture and required components
- CloudFormation parameters, intrinsic functions, resources and outputs
- Resource dependencies in CloudFormation

## Tested Environments

- AWS CloudShell (Bash)
- Ubuntu 24.04/26.04, AWS CLI 2.x, Node.js 20+

## Prerequisites

Before starting, ensure you have:
- An AWS account (see [`1-cloud-account/aws`](../../1-cloud-account/aws/readme.md))
- AWS CloudShell (or the AWS CLI installed and signed in on your machine)
- Basic understanding of AWS Lambda (complete the [AWS version of Exercise 10](../../10-faas-functions/aws/readme.md) first)

---

## Part 1: Understand the CloudFormation Template

### Step 1: Examine the Template

Open [`template.yaml`](template.yaml) and review its structure. Let's break down the key components:

**Parameters** (lines 6-27):
```yaml
Parameters:
  Runtime:
    Type: String
    Default: nodejs24.x
    AllowedValues:
      - nodejs24.x
      - nodejs22.x
  MemorySize:
    Type: Number
    Default: 128
    AllowedValues: [128, 256, 512]
  LogRetentionInDays:
    Type: Number
    Default: 7
```

- `Runtime`: Node.js version of the function (`AllowedValues` restricts it, like `@allowed` in Bicep)
- `MemorySize`: Memory of the function in MB (Lambda gives more CPU with more memory)
- `LogRetentionInDays`: How long CloudWatch Logs keeps the logs

All parameters have defaults, so you don't have to pass any of them.

**Resources** (lines 29-100):

1. **FunctionRole** (lines 30-50): The IAM role the function runs with. The trust policy says that only Lambda may use it, and the inline policy lets the function write to its log group - nothing else
2. **FunctionLogGroup** (lines 52-57): The log group of the function. Lambda would create it automatically on the first call, but then it wouldn't belong to the stack and wouldn't be deleted with it
3. **Function** (lines 59-76): The Lambda function. Its inline code (`ZipFile`) is a placeholder; you'll upload your own code in Part 3
4. **FunctionUrl** (lines 78-83): The HTTPS address of the function. `AuthType: NONE` makes it public, like the authorization level Anonymous in Azure
5. **FunctionUrlPermission** and **FunctionInvokePermission** (lines 85-100): Two permissions allow the public calls: one for the URL and one for running the function through it (without the second one the URL answers `403 Forbidden`)

**Outputs** (lines 102-111): The function name, its URL and the log group, shown after the deployment.

**Key CloudFormation Concepts Demonstrated:**

- **`!Ref`**: Returns a parameter value or the main identifier of a resource (`!Ref Function` is the function name)
- **`!GetAtt`**: Returns an attribute of a resource (`!GetAtt FunctionRole.Arn`, `!GetAtt FunctionUrl.FunctionUrl`)
- **`!Sub`**: Builds a string with variables (`${AWS::StackName}-function`); `AWS::StackName` is a **pseudo parameter** that CloudFormation fills in itself
- **Resource dependencies**: `!Ref` and `!GetAtt` make CloudFormation create the referenced resource first - the role and the log group before the function, the function before its URL (like implicit dependencies in Bicep)
- **Logical ID vs physical ID**: `Function` is the logical ID (the name inside the template), `cloud-computing-faas-function` is the physical ID (the real name in AWS)

---

## Part 2: Deploy with CloudFormation

### Step 2: Download the Template

Open **AWS CloudShell** from the AWS Console (the terminal icon in the top bar), in the region you want to use.

**Option A: Using Bash (recommended)**

**Set the stack name:**

```bash
STACK_NAME="cloud-computing-faas"
```

Set the AWS region (change if needed):

```bash
REGION="eu-west-2"
```

**Download the template and the function code:**

```bash
mkdir -p cloudformation-faas/my-function && cd cloudformation-faas
BASE_URL="https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/12-iac-serverless-functions/aws"
curl -o template.yaml $BASE_URL/template.yaml
curl -o my-function/index.mjs $BASE_URL/my-function/index.mjs
curl -o my-function/test-locally.mjs $BASE_URL/my-function/test-locally.mjs
```

**Option B: Using PowerShell**

Switch CloudShell to PowerShell with `pwsh`.

**Set the stack name:**

```powershell
$STACK_NAME="cloud-computing-faas"
```

Set the AWS region (change if needed):

```powershell
$REGION="eu-west-2"
```

**Download the template and the function code:**

```powershell
New-Item -ItemType Directory -Force cloudformation-faas/my-function | Out-Null; Set-Location cloudformation-faas
$BASE_URL="https://raw.githubusercontent.com/lsawicki-cdv/course-iot-cloud-computing/refs/heads/main/12-iac-serverless-functions/aws"
curl -o template.yaml "$BASE_URL/template.yaml"
curl -o my-function/index.mjs "$BASE_URL/my-function/index.mjs"
curl -o my-function/test-locally.mjs "$BASE_URL/my-function/test-locally.mjs"
```

### Step 3: Deploy the CloudFormation Template

**Option A: Using Bash (recommended)**

**Deploy using AWS CLI:**

```bash
aws cloudformation deploy \
  --region $REGION \
  --stack-name $STACK_NAME \
  --template-file template.yaml \
  --capabilities CAPABILITY_IAM
```

**Option B: Using PowerShell**

**Deploy using AWS CLI:**

```powershell
aws cloudformation deploy `
  --region $REGION `
  --stack-name $STACK_NAME `
  --template-file template.yaml `
  --capabilities CAPABILITY_IAM
```

This command:
1. Uploads the template to CloudFormation
2. Creates a **change set** - the list of resources to create, change or delete
3. Executes the change set and waits until the stack is ready
4. Rolls back (deletes what it created) if any resource fails

`--capabilities CAPABILITY_IAM` confirms that you know the template creates an IAM role. Without it, CloudFormation refuses to deploy (`InsufficientCapabilities`).

**Wait about 1 minute for the deployment to complete**. You'll see output like:

```
Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - cloud-computing-faas
```

**Important**: Look for `Successfully created/updated stack` to confirm successful deployment.

### Step 4: Verify Deployment

**Option A: Using Bash (recommended)**

**List deployed resources:**

```bash
aws cloudformation describe-stack-resources \
  --region $REGION \
  --stack-name $STACK_NAME \
  --query "StackResources[].[LogicalResourceId,ResourceType,ResourceStatus]" \
  --output table
```

**Show the outputs of the stack:**

```bash
aws cloudformation describe-stacks \
  --region $REGION \
  --stack-name $STACK_NAME \
  --query "Stacks[0].Outputs" \
  --output table
```

**Save the function name and URL:**

```bash
FUNCTION_NAME=$(aws cloudformation describe-stacks --region $REGION --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)
FUNCTION_URL=$(aws cloudformation describe-stacks --region $REGION --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" --output text)
echo "Function: $FUNCTION_NAME"
echo "Function URL: $FUNCTION_URL"
```

**Call the placeholder code:**

```bash
curl "$FUNCTION_URL"
```

**Option B: Using PowerShell**

**List deployed resources:**

```powershell
aws cloudformation describe-stack-resources `
  --region $REGION `
  --stack-name $STACK_NAME `
  --query "StackResources[].[LogicalResourceId,ResourceType,ResourceStatus]" `
  --output table
```

**Show the outputs of the stack:**

```powershell
aws cloudformation describe-stacks `
  --region $REGION `
  --stack-name $STACK_NAME `
  --query "Stacks[0].Outputs" `
  --output table
```

**Save the function name and URL:**

```powershell
$FUNCTION_NAME=$(aws cloudformation describe-stacks --region $REGION --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)
$FUNCTION_URL=$(aws cloudformation describe-stacks --region $REGION --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" --output text)
echo "Function: $FUNCTION_NAME"
echo "Function URL: $FUNCTION_URL"
```

**Call the placeholder code:**

```powershell
curl "$FUNCTION_URL"
```

You should see 6 resources, all `CREATE_COMPLETE`:
- `FunctionRole` (`AWS::IAM::Role`)
- `FunctionLogGroup` (`AWS::Logs::LogGroup`)
- `Function` (`AWS::Lambda::Function`)
- `FunctionUrl` (`AWS::Lambda::Url`)
- `FunctionUrlPermission` and `FunctionInvokePermission` (`AWS::Lambda::Permission`)

The placeholder code answers `The function works, but your code is not deployed yet.`

---

## Part 3: Deploy a Function to Your Lambda

Your function infrastructure is ready, but it runs only the placeholder code. Let's deploy a simple HTTP function.

### Step 5: Look at the Function Code

Open `my-function/index.mjs`. It does the same as the function that `func new --template "HTTP trigger"` creates in the Azure version:

```javascript
export const handler = async (event) => {
    console.log(`Http function processed request for url "${event.rawPath}"`);

    // The request body arrives base64-encoded when it isn't text
    const body = event.body && event.isBase64Encoded
        ? Buffer.from(event.body, 'base64').toString()
        : event.body;
    const name = event.queryStringParameters?.name || body || 'world';

    return {
        statusCode: 200,
        headers: { 'Content-Type': 'text/plain' },
        body: `Hello, ${name}!`
    };
};
```

- `handler` is the function Lambda calls; the template sets `Handler: index.handler` (file `index`, function `handler`)
- `event` is the HTTP request from the function URL: the query string in `queryStringParameters`, the body in `body`
- The return value is the HTTP response: status code, headers and body
- `.mjs` makes the file an ES module, so it can use `export`; it needs no npm packages

### Step 6: Test Locally (Optional)

`my-function/test-locally.mjs` calls the handler with an event like the one Lambda sends:

```bash
cd my-function
node test-locally.mjs
cd ..
```

You should see the response with `body: 'Hello, AWS!'`.

### Step 7: Deploy the Function Code to AWS

**Option A: Using Bash (recommended)**

**Pack the code into a zip file:**

```bash
cd my-function && zip ../my-function.zip index.mjs && cd ..
```

**Upload the code and wait until the function is updated:**

```bash
aws lambda update-function-code \
  --region $REGION \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://my-function.zip \
  --query "[FunctionName,LastUpdateStatus]" \
  --output text

aws lambda wait function-updated --region $REGION --function-name $FUNCTION_NAME
```

**Option B: Using PowerShell**

**Pack the code into a zip file:**

```powershell
Set-Location my-function; zip ../my-function.zip index.mjs; Set-Location ..
```

**Upload the code and wait until the function is updated:**

```powershell
aws lambda update-function-code `
  --region $REGION `
  --function-name $FUNCTION_NAME `
  --zip-file fileb://my-function.zip `
  --query "[FunctionName,LastUpdateStatus]" `
  --output text

aws lambda wait function-updated --region $REGION --function-name $FUNCTION_NAME
```

The new code replaces the placeholder. The new file is `index.mjs` and the placeholder was `index.js`; both match `Handler: index.handler`.

**Note**: The code is now managed outside the template. CloudFormation uploads the placeholder again only if you change the `ZipFile` code in the template. In real projects the code goes into the template too, e.g. with AWS SAM (`sam deploy`) or `aws cloudformation package`, which upload the zip file to S3 and put its location into the template.

### Step 8: Test Your Deployed Function

**Option A: Using Bash (recommended)**

```bash
curl "${FUNCTION_URL}?name=CloudFormation"
```

**Option B: Using PowerShell**

```powershell
curl "${FUNCTION_URL}?name=CloudFormation"
```

**Expected response:**

```
Hello, CloudFormation!
```

**Congratulations!** You've deployed AWS infrastructure using CloudFormation and deployed a function to it.

---

## Part 4: Understanding the Deployment

### Step 9: Explore What Was Created

**View the stack in the AWS Console:**

1. Open **CloudFormation** → **Stacks** → `cloud-computing-faas`
2. **Events** tab: every step of the deployment, in order - this is where you find the reason when a deployment fails
3. **Resources** tab: the logical and physical IDs of the 6 resources, with links to them
4. **Outputs** tab: the function name, URL and log group
5. **Template** tab: the template that was deployed
6. **Parameters** tab: the values used (the defaults, because you passed none)

**Check the logs of the function:**

1. Open **CloudWatch** → **Log groups** → `/aws/lambda/cloud-computing-faas-function`
2. Open the newest log stream and find `Http function processed request for url "/"`

Or in CloudShell:

```bash
aws logs tail /aws/lambda/cloud-computing-faas-function --region $REGION --since 15m
```

**View the function configuration:**

1. Open **Lambda** → **Functions** → `cloud-computing-faas-function`
2. **Configuration** → **General configuration**: memory (128 MB) and timeout (10 s) from the template
3. **Configuration** → **Function URL**: auth type `NONE`
4. **Configuration** → **Permissions**: the execution role and the resource-based policy with the two permissions
5. **Configuration** → **Monitoring and operations tools**: the log group from the template

---

## CloudFormation Best Practices

### Nested Stacks

For larger projects, split the template into smaller templates (like Bicep modules):

```yaml
Resources:
  FunctionStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://my-bucket.s3.eu-west-2.amazonaws.com/function.yaml
      Parameters:
        Runtime: nodejs24.x
```

Nested templates must be in an S3 bucket; `aws cloudformation package` uploads them for you.

### Parameter Files

Create separate parameter files for different environments:

**dev-parameters.json:**

```json
[
  "Runtime=nodejs24.x",
  "MemorySize=256"
]
```

Deploy with:

**Using Bash:**

```bash
aws cloudformation deploy \
  --region $REGION \
  --stack-name $STACK_NAME \
  --template-file template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides file://dev-parameters.json
```

**Using PowerShell:**

```powershell
aws cloudformation deploy `
  --region $REGION `
  --stack-name $STACK_NAME `
  --template-file template.yaml `
  --capabilities CAPABILITY_IAM `
  --parameter-overrides file://dev-parameters.json
```

### Outputs

Outputs return information about the deployed resources. `template.yaml` ends with three of them:

```yaml
Outputs:
  FunctionName:
    Value: !Ref Function
  FunctionUrl:
    Value: !GetAtt FunctionUrl.FunctionUrl
  LogGroupName:
    Value: !Ref FunctionLogGroup
```

Add `Export: Name: ...` to an output to use it in another stack with `!ImportValue`.

### Stateful Resources

Set `DeletionPolicy: Retain` on resources with data (S3 buckets, DynamoDB tables, databases), so deleting the stack doesn't delete your data.

---

## Troubleshooting

### Deployment fails with "Template format error" or "ValidationError"

- **Check the template syntax**: Run `aws cloudformation validate-template --template-body file://template.yaml`
- **Check the YAML indentation**: YAML uses spaces, not tabs
- **Check more thoroughly**: Run `cfn-lint template.yaml` (`pip install cfn-lint`); it also checks property names and values

### Deployment fails with "Requires capabilities : [CAPABILITY_IAM]"

- **Add `--capabilities CAPABILITY_IAM`**: The template creates an IAM role

### Stack is in `ROLLBACK_COMPLETE` state

- **The first deployment failed** and CloudFormation deleted the resources. Find the reason in the **Events** tab (the first `CREATE_FAILED` event) or with:
  ```bash
  aws cloudformation describe-stack-events --region $REGION --stack-name $STACK_NAME --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" --output table
  ```
- **Delete the stack** (see Cleanup) and deploy again - a stack in `ROLLBACK_COMPLETE` can't be updated

### "No changes to deploy. Stack cloud-computing-faas is up to date"

- **Nothing changed in the template or the parameters**: This is not an error

### Function URL returns `403 Forbidden`

- **Check the permissions**: Both `FunctionUrlPermission` and `FunctionInvokePermission` must be in the stack (Lambda → Configuration → Permissions → Resource-based policy statements)
- **Your account may block public function URLs**: Some organization policies don't allow `AuthType: NONE`; use `aws lambda invoke` instead

### Function returns `Internal Server Error`

- **Check the logs**: `aws logs tail /aws/lambda/cloud-computing-faas-function --region $REGION --since 15m`
- **Check the code**: Review `my-function/index.mjs` for syntax errors; run `node test-locally.mjs`
- **Check the handler**: The file must be `index.mjs` (or `index.js`) at the top of the zip file, not inside a folder

---

## Cleanup

**Important:** Delete all resources to avoid charges once the Free Tier ends!

### Option 1: Delete the Stack (Recommended)

This deletes all resources created by the template - the stack is the AWS counterpart of the resource group:

**Using Bash:**

```bash
aws cloudformation delete-stack --region $REGION --stack-name $STACK_NAME
aws cloudformation wait stack-delete-complete --region $REGION --stack-name $STACK_NAME
```

**Using PowerShell:**

```powershell
aws cloudformation delete-stack --region $REGION --stack-name $STACK_NAME
aws cloudformation wait stack-delete-complete --region $REGION --stack-name $STACK_NAME
```

### Option 2: Delete Individual Resources

Don't delete the resources of a stack one by one: the stack would still list them, and the next update or delete of the stack could fail (this difference between the template and the real resources is called **drift**). Remove a resource from the template and deploy again instead - CloudFormation then deletes that resource.

**Delete the local files** (CloudShell keeps them):

```bash
cd ~ && rm -rf cloudformation-faas
```

---

## Summary and Learning Outcomes

Congratulations! You've successfully deployed AWS Lambda using Infrastructure as Code. You learned:

✅ **CloudFormation Fundamentals**: Parameters, resources, intrinsic functions and outputs
✅ **IaC Benefits**: Repeatable, version-controlled, automated deployments
✅ **AWS Lambda Architecture**: Execution role, function, function URL, permissions and logs
✅ **Resource Dependencies**: How `!Ref` and `!GetAtt` decide the deployment order
✅ **AWS CLI**: Deploying CloudFormation templates and managing stacks
✅ **Function Deployment**: Uploading code to AWS-managed infrastructure
✅ **Monitoring**: CloudWatch Logs integration for observability

### Why Infrastructure as Code?

**Traditional Approach (Manual):**
- Click through the AWS Console (time-consuming)
- Hard to replicate exactly
- No version history
- Difficult to share with team
- Error-prone

**IaC Approach (CloudFormation):**
- ✅ Define infrastructure in code
- ✅ Version control with Git
- ✅ Deploy multiple environments consistently
- ✅ Easy to review and collaborate
- ✅ Automated and repeatable, with automatic rollback

### CloudFormation vs Bicep

The same kind of resource in both languages:

**CloudFormation (YAML):**

```yaml
FunctionLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub /aws/lambda/${AWS::StackName}-function
    RetentionInDays: !Ref LogRetentionInDays
```

**Bicep:**

```bicep
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: appInsightsLocation
  properties: {
    retentionInDays: 30
  }
}
```

Bicep names an API version for every resource type; CloudFormation has one version of each resource type that AWS updates in place.

## Optional Next Steps

- Explore the template and modify parameters (try `MemorySize=256` with `--parameter-overrides`) and see what the change set changes
- Add another output to the template, e.g. the ARN of the execution role (`!GetAtt FunctionRole.Arn`)
- Create a parameter file for different environments (dev, staging, production) and deploy two stacks with different names
- Rewrite the template with AWS SAM (`AWS::Serverless::Function`), which also uploads the code (`sam deploy`)
- Compare this exercise with Exercise 14 (Terraform) to understand different IaC approaches
- Implement a CI/CD pipeline using GitHub Actions to deploy the template automatically

## Additional Resources

- [AWS CloudFormation User Guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [CloudFormation resource and property reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/introduction.html)
- [AWS::Lambda::Url reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-lambda-url.html)
- [CloudFormation best practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)
- [cfn-lint](https://github.com/aws-cloudformation/cfn-lint)

---

## Reference Commands

**Option A: Using Bash (recommended)**

**Validate the template:**

```bash
aws cloudformation validate-template --region $REGION --template-body file://template.yaml
```

**Preview changes before deployment (change set, like What-If):**

```bash
aws cloudformation deploy \
  --region $REGION \
  --stack-name $STACK_NAME \
  --template-file template.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides MemorySize=256 \
  --no-execute-changeset
```

The command prints an `aws cloudformation describe-change-set` command that shows the changes; run `aws cloudformation execute-change-set --change-set-name <ARN>` to apply them, or `aws cloudformation delete-change-set --change-set-name <ARN>` to drop them.

**View the failed steps of a deployment:**

```bash
aws cloudformation describe-stack-events \
  --region $REGION \
  --stack-name $STACK_NAME \
  --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" \
  --output table
```

**Create a template from existing resources:** use the **IaC generator** in the CloudFormation console (CloudFormation → IaC generator).

**Option B: Using PowerShell**

**Validate the template:**

```powershell
aws cloudformation validate-template --region $REGION --template-body file://template.yaml
```

**Preview changes before deployment (change set, like What-If):**

```powershell
aws cloudformation deploy `
  --region $REGION `
  --stack-name $STACK_NAME `
  --template-file template.yaml `
  --capabilities CAPABILITY_IAM `
  --parameter-overrides MemorySize=256 `
  --no-execute-changeset
```

The command prints an `aws cloudformation describe-change-set` command that shows the changes; run `aws cloudformation execute-change-set --change-set-name <ARN>` to apply them, or `aws cloudformation delete-change-set --change-set-name <ARN>` to drop them.

**View the failed steps of a deployment:**

```powershell
aws cloudformation describe-stack-events `
  --region $REGION `
  --stack-name $STACK_NAME `
  --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" `
  --output table
```

**Create a template from existing resources:** use the **IaC generator** in the CloudFormation console (CloudFormation → IaC generator).
