# Azure Functions - Serverless Computing Exercise

> Using AWS instead? Follow the [AWS version of this exercise](aws/readme.md).

In this exercise, you will learn how to create and deploy serverless functions using Azure Functions. You'll build an HTTP-triggered function, test it locally, and deploy it to Azure. In Part 5 you'll turn a function into a small **AI agent** that answers questions about IoT devices with a model from Azure OpenAI in Microsoft Foundry.

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

## What are Azure Functions?

**Azure Functions** is a serverless compute service that lets you run event-driven code without managing infrastructure. Key features:

- **Serverless**: No servers to manage - Azure handles scaling automatically
- **Pay-per-execution**: Only pay when your function runs
- **Event-driven**: Triggers from HTTP requests, timers, queues, databases, etc.
- **Multiple languages**: Python, JavaScript, C#, Java, PowerShell, TypeScript
- **Built-in scaling**: Automatically scales based on demand

### Common Use Cases

- **REST APIs**: Create lightweight HTTP endpoints
- **Webhooks**: Process events from external services
- **Scheduled tasks**: Run code on a schedule (cron jobs)
- **Data processing**: Process IoT data, file uploads, database changes
- **Microservices**: Build small, independent services

## Tested Environments

- Ubuntu 24.04 / 26.04
- Python 3.10+ locally, Python 3.13 in Azure
- Azure Functions Core Tools v4

## Prerequisites

Before starting, ensure you have:
- Azure account with active subscription
- Python 3.10 or higher installed
- VS Code installed
- Basic understanding of HTTP and REST APIs

---

## Part 1: Setup Your Development Environment

### Step 1: Install Required Software

**Install Python** (if not already installed):
- **macOS/Linux**: Use your package manager or download from [python.org](https://www.python.org/downloads/)
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

**Verify Python installation:**
```bash
python3 --version  # macOS/Linux
python --version   # Windows
```

### Step 2: Install Azure Functions Core Tools

**macOS:**
```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
```

**Windows:**

Download and install from: https://go.microsoft.com/fwlink/?linkid=2174087

Or using Chocolatey:
```powershell
choco install azure-functions-core-tools-4
```

**Ubuntu/Debian Linux:**
```bash
# Import Microsoft GPG key
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg

# Add Microsoft package repository
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'

# Install Azure Functions Core Tools
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

**Verify installation:**
```bash
func --version
```

You should see version 4.x.x

### Step 3: Install VS Code Extensions

Open VS Code and install these extensions:

1. **Azure Functions** (Microsoft)
   - Search for "Azure Functions" in Extensions
   - Click Install

2. **Python** (Microsoft)
   - Search for "Python" in Extensions
   - Click Install

3. **Azure Account** (Microsoft)
   - Search for "Azure Account" in Extensions
   - Click Install

4. **Azurite** (Microsoft) - Optional, for local storage emulation
   - Search for "Azurite" in Extensions
   - Click Install

---

## Part 2: Create Your First Azure Function Locally

### Step 4: Create Function Project in VS Code

1. Open VS Code
2. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS) to open Command Palette
3. Type "Azure Functions: Create New Project" and select it
4. Choose a folder for your project (or use the existing `10-faas-functions` directory)
5. Select **Python** as the language
6. Select **Model V2** (recommended for new projects)
7. Select your Python interpreter (Python 3.10+)
8. Select **HTTP trigger** as the template
9. Enter function name: **HttpTrigger1**
10. Authorization level: **Anonymous** (for learning purposes)

**What just happened?**
VS Code created a Function App project with these files:
- `function_app.py` - Your function code
- `host.json` - Function app configuration
- `local.settings.json` - Local development settings
- `requirements.txt` - Python dependencies
- `.vscode/` - VS Code configuration

### Step 5: Understanding the Function Code

Open `function_app.py` and examine the code:

```python
import azure.functions as func
import logging

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.function_name(name="HttpTrigger1")
@app.route(route="hello")
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(
            f"Hello, {name}. This HTTP-triggered function executed successfully."
        )
    else:
        return func.HttpResponse(
            "This HTTP-triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
            status_code=200
        )
```

The `function_app.py` in this folder also contains the AI agent function from Part 5 (`AgentTrigger`); you can ignore it until then.

**Key concepts:**
- `http_auth_level=func.AuthLevel.ANONYMOUS` - by default anyone can call the functions, without a key
- `@app.route(route="hello")` - Function responds to `/api/hello` endpoint
- `req.params.get('name')` - Get query parameter from URL
- `req.get_json()` - Get JSON body from POST request
- `func.HttpResponse` - Return HTTP response to caller

### Step 6: Install Python Dependencies

Open terminal in VS Code (`Ctrl+`` or `View` → `Terminal`).

**Create virtual environment:**

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
py -m venv .venv
.venv\Scripts\activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### Step 7: Test Function Locally

**Start the local function runtime:**

In the VS Code terminal:
```bash
func start
```

You should see output like:
```
Azure Functions Core Tools
Core Tools Version: 4.x.x
Function Runtime Version: 4.x.x

Functions:
  HttpTrigger1: [GET,POST] http://localhost:7071/api/hello
```

**The function is now running locally!**

### Step 8: Test Your Function

**Option 1: Test in web browser**

Open your browser and navigate to:
```
http://localhost:7071/api/hello?name=YourName
```

You should see:
```
Hello, YourName. This HTTP-triggered function executed successfully.
```

**Option 2: Test with curl**

Open a new terminal (keep the function running in the first terminal):

```bash
# Test with query parameter
curl "http://localhost:7071/api/hello?name=Student"

# Test with JSON body
curl -X POST http://localhost:7071/api/hello \
  -H "Content-Type: application/json" \
  -d '{"name":"Student"}'
```

**Option 3: Test with VS Code REST Client**

If you have the REST Client extension installed, create a file `test.http`:

```http
### Test GET with query parameter
GET http://localhost:7071/api/hello?name=Student

### Test POST with JSON body
POST http://localhost:7071/api/hello
Content-Type: application/json

{
  "name": "Student"
}
```

Click "Send Request" above each test.

**Stop the function:** Press `Ctrl+C` in the terminal running the function.

---

## Part 3: Deploy Function to Azure

### Step 9: Sign in to Azure

1. In VS Code, click the **Azure** icon in the left sidebar
2. In the **Resources** section, click **Sign in to Azure**
3. Follow the prompts to sign in to your Azure account
4. Select your subscription

### Step 10: Create Azure Function App

You can create the Function App either through VS Code or Azure Cloud Shell.

**Option A: Using VS Code (Recommended)**

1. Press `Ctrl+Shift+P` to open Command Palette
2. Type "Azure Functions: Create Function App in Azure (Advanced)"
3. Enter a **globally unique name** for your Function App (e.g., `func-yourname-12345`)
4. Select **Flex Consumption** plan (pay-per-execution, the recommended serverless plan)
5. Select **Python 3.13** runtime
6. Keep the default instance memory (2048 MB)
7. Select **UK South** (or your allowed region)
8. Create new resource group: `myResourceGroupFunctions`
9. Create new Storage Account (accept default name)
10. Create new Application Insights (accept default name)

Wait 1-2 minutes for deployment to complete.

**Option B: Using Azure Cloud Shell**

Open **Azure Cloud Shell** from the Azure Portal.

**Option A: Using Bash (recommended)**

Set environment variables:
```bash
RESOURCE_GROUP="myResourceGroupFunctions"
```
```bash
LOCATION="uksouth"  # Change to your allowed region
```
```bash
FUNCTION_APP_NAME="func-yourname-12345"  # Must be globally unique
```
```bash
STORAGE_ACCOUNT="funcstorage$(openssl rand -hex 3)"
```

Create resources:
```bash
# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```
```bash
# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS
```
```bash
# Create Function App
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP_NAME \
  --storage-account $STORAGE_ACCOUNT \
  --flexconsumption-location $LOCATION \
  --runtime python \
  --runtime-version 3.13
```

**Option B: Using PowerShell**

Set environment variables (PowerShell syntax):
```powershell
$RESOURCE_GROUP="myResourceGroupFunctions"
```
```powershell
$LOCATION="uksouth"  # Change to your allowed region
```
```powershell
$FUNCTION_APP_NAME="func-yourname-12345"  # Must be globally unique
```
```powershell
$STORAGE_ACCOUNT="funcstorage$(Get-Random -Minimum 100000 -Maximum 999999)"
```

Create resources:
```powershell
# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```
```powershell
# Create storage account
az storage account create `
  --name $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --sku Standard_LRS
```
```powershell
# Create Function App
az functionapp create `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP_NAME `
  --storage-account $STORAGE_ACCOUNT `
  --flexconsumption-location $LOCATION `
  --runtime python `
  --runtime-version 3.13
```

### Step 11: Deploy Your Function Code to Azure

**Option 1: Deploy via VS Code (Recommended)**

1. In VS Code, open the Azure Functions extension
2. Find your Function App in the **Resources** section
3. Right-click your Function App name
4. Select **Deploy to Function App**
5. Confirm the deployment
6. Wait 1-2 minutes for deployment to complete

VS Code will show deployment progress and display the function URL when complete.

**Option 2: Deploy via Azure Functions Core Tools**

From your project directory:
```bash
func azure functionapp publish func-yourname-12345
```

Replace `func-yourname-12345` with your Function App name.

### Step 12: Get Your Function URL

**Option A: From VS Code**

After deployment, VS Code displays the function URL in the output window.

**Option B: From Azure Portal**

1. Navigate to Azure Portal
2. Go to your Function App
3. Click **Functions** in the left menu
4. Click **HttpTrigger1**
5. Click **Get Function URL**
6. Copy the URL

**Option C: Using Azure CLI**

**Using Bash:**
```bash
az functionapp function show \
  --resource-group myResourceGroupFunctions \
  --name func-yourname-12345 \
  --function-name HttpTrigger1 \
  --query invokeUrlTemplate \
  --output tsv
```

**Using PowerShell:**
```powershell
az functionapp function show `
  --resource-group myResourceGroupFunctions `
  --name func-yourname-12345 `
  --function-name HttpTrigger1 `
  --query invokeUrlTemplate `
  --output tsv
```

### Step 13: Test Your Deployed Function

**Test in web browser:**
```
https://func-yourname-12345.azurewebsites.net/api/hello?name=Student
```

**Test with curl:**
```bash
curl "https://func-yourname-12345.azurewebsites.net/api/hello?name=Student"
```

You should see the same response as when testing locally!

### Step 14: Monitor Your Function

**View logs in Azure Portal:**

1. Navigate to your Function App in Azure Portal
2. Click **Functions** → **HttpTrigger1**
3. Click **Monitor**
4. View execution history and logs

**View logs in VS Code:**

1. Right-click your Function App in the Azure Functions extension
2. Select **Start Streaming Logs**
3. Make a request to your function
4. See real-time logs in VS Code output

**View Application Insights:**

1. Navigate to your Function App in Azure Portal
2. Click **Application Insights** in the left menu
3. Click **View Application Insights data**
4. Explore metrics, performance, and failures

---

## Part 4: Enhance Your Function (Optional)

### Step 15: Add a Second Function - Timer Trigger

Let's add a scheduled function that runs every minute.

**Add to `function_app.py`:**

```python
@app.function_name(name="TimerTrigger1")
@app.schedule(schedule="0 */1 * * * *", arg_name="timer")
def timer_function(timer: func.TimerRequest) -> None:
    logging.info('Python timer trigger function executed.')

    if timer.past_due:
        logging.info('The timer is past due!')

    logging.info('Timer trigger function ran at %s', timer.schedule_status)
```

**Deploy the updated function:**
1. Save the file
2. Deploy to Azure again using VS Code or `func azure functionapp publish`
3. Check the logs to see it running every minute

### Step 16: Add Environment Variables

**Add configuration to your function:**

1. In Azure Portal, navigate to your Function App
2. Click **Configuration** in the left menu
3. Click **+ New application setting**
4. Name: `GREETING_MESSAGE`, Value: `Welcome`
5. Click **OK** and **Save**

**Update your function to use it:**

```python
import os

@app.function_name(name="HttpTrigger1")
@app.route(route="hello")
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    greeting = os.environ.get('GREETING_MESSAGE', 'Hello')
    name = req.params.get('name')

    if name:
        return func.HttpResponse(f"{greeting}, {name}!")
    else:
        return func.HttpResponse(f"{greeting}! Pass a name parameter.")
```

Deploy and test to see the new greeting message.

---

## Part 5: Build an AI Agent with Azure OpenAI in Foundry

An **AI agent** is a program in which a language model decides which actions to take. Here the model answers questions about IoT devices, such as "Is any device too hot?". It doesn't know the readings itself, so it asks your code to run **tools** - ordinary Python functions - and uses their results in the answer.

The model comes from **Azure OpenAI in Microsoft Foundry Models** (a `gpt-5.4-mini` deployment). Every question costs a fraction of a cent; it is paid from your Azure credit.

**The agent loop** (in `ask_agent()` in `function_app.py`):
1. Send the question and the list of tools to the model
2. If the model asks for a tool (`tool_calls` in the answer), run it and send the result back
3. Repeat until the model answers with text - or stop after 5 model calls (`MAX_STEPS`), so a confused model can't run (and cost) forever

**The files:**
- `sensor_tools.py` - the tools: `list_devices` and `get_sensor_reading` return simulated data for three devices, with a description and a JSON schema of the input for the model. `run_tool()` checks the input the model sends, because the model's output is untrusted. The AWS version of this exercise uses the same file
- `function_app.py` - the `AgentTrigger` function (`POST /api/agent`) runs the loop with the `openai` Python package. Unlike `hello`, it needs a **function key** (`auth_level=func.AuthLevel.FUNCTION`), so nobody else can spend your credit

### Step 17: Create a Foundry Resource and Deploy a Model

In **Azure Cloud Shell**:

**Option A: Using Bash (recommended)**

Set environment variables:
```bash
RESOURCE_GROUP="myResourceGroupFunctions"
```
```bash
LOCATION="uksouth"  # Change to your allowed region
```
```bash
AI_NAME="ai-iot-agent-$(openssl rand -hex 3)"  # Must be globally unique
```
```bash
MODEL_DEPLOYMENT="gpt-5.4-mini"
```

Create the Foundry resource (it takes 1-2 minutes):
```bash
az cognitiveservices account create \
  --name $AI_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --kind AIServices \
  --sku S0 \
  --custom-domain $AI_NAME \
  --yes
```

Deploy the model (capacity 10 = 10,000 tokens per minute):
```bash
az cognitiveservices account deployment create \
  --name $AI_NAME \
  --resource-group $RESOURCE_GROUP \
  --deployment-name $MODEL_DEPLOYMENT \
  --model-name gpt-5.4-mini \
  --model-version 2026-03-17 \
  --model-format OpenAI \
  --sku-name GlobalStandard \
  --sku-capacity 10
```

Show the endpoint and the key, and save them for the next steps:
```bash
az cognitiveservices account show --name $AI_NAME --resource-group $RESOURCE_GROUP --query properties.endpoint --output tsv
```
```bash
az cognitiveservices account keys list --name $AI_NAME --resource-group $RESOURCE_GROUP --query key1 --output tsv
```

**Option B: Using PowerShell**

Set environment variables (PowerShell syntax):
```powershell
$RESOURCE_GROUP="myResourceGroupFunctions"
```
```powershell
$LOCATION="uksouth"  # Change to your allowed region
```
```powershell
$AI_NAME="ai-iot-agent-$(Get-Random -Minimum 100000 -Maximum 999999)"  # Must be globally unique
```
```powershell
$MODEL_DEPLOYMENT="gpt-5.4-mini"
```

Create the Foundry resource (it takes 1-2 minutes):
```powershell
az cognitiveservices account create `
  --name $AI_NAME `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --kind AIServices `
  --sku S0 `
  --custom-domain $AI_NAME `
  --yes
```

Deploy the model (capacity 10 = 10,000 tokens per minute):
```powershell
az cognitiveservices account deployment create `
  --name $AI_NAME `
  --resource-group $RESOURCE_GROUP `
  --deployment-name $MODEL_DEPLOYMENT `
  --model-name gpt-5.4-mini `
  --model-version 2026-03-17 `
  --model-format OpenAI `
  --sku-name GlobalStandard `
  --sku-capacity 10
```

Show the endpoint and the key, and save them for the next steps:
```powershell
az cognitiveservices account show --name $AI_NAME --resource-group $RESOURCE_GROUP --query properties.endpoint --output tsv
```
```powershell
az cognitiveservices account keys list --name $AI_NAME --resource-group $RESOURCE_GROUP --query key1 --output tsv
```

**Important:** The key works like a password. Don't share it and don't write it into files that you commit to git.

If `gpt-5.4-mini` isn't available in your region, list the models you can deploy and pick another small one (for example `gpt-5-mini`), with its version:
```bash
az cognitiveservices model list --location $LOCATION --query "[?kind=='OpenAI' && contains(model.name,'mini')].{name:model.name,version:model.version}" --output table
```

### Step 18: Look at the Agent Code

Open `function_app.py` and find `ask_agent()`:
- `OpenAI(base_url=<endpoint>/openai/v1/, api_key=<key>)` - the `openai` package talks to Azure OpenAI through its OpenAI-compatible v1 API
- `tools = [{"type": "function", "function": tool} for tool in TOOLS]` - the tools from `sensor_tools.py` in the format of the Chat Completions API
- `client.chat.completions.create(..., tools=tools, max_completion_tokens=500)` - one model call; always limit the length of the answer
- `message.tool_calls` - the tools the model wants to run. Each result goes back as a message with `"role": "tool"`

The answer of the function contains the model's `answer` and the `steps` - every tool the model called, with its input and result - so you can see how the agent worked.

### Step 19: Test the Agent Locally

Install the new dependency (`openai`) in your virtual environment:
```bash
pip install -r requirements.txt
```

Set the connection details as environment variables in the terminal where you will run `func start` (the Functions runtime passes them to your code). Use the endpoint and the key from Step 17:

**macOS/Linux:**
```bash
export AZURE_OPENAI_ENDPOINT="https://ai-iot-agent-<id>.cognitiveservices.azure.com/"
export AZURE_OPENAI_API_KEY="<your-key>"
export AZURE_OPENAI_DEPLOYMENT="gpt-5.4-mini"
```

**Windows (PowerShell):**
```powershell
$env:AZURE_OPENAI_ENDPOINT="https://ai-iot-agent-<id>.cognitiveservices.azure.com/"
$env:AZURE_OPENAI_API_KEY="<your-key>"
$env:AZURE_OPENAI_DEPLOYMENT="gpt-5.4-mini"
```

Start the functions:
```bash
func start
```

You should see both functions:
```
Functions:
        AgentTrigger: [POST] http://localhost:7071/api/agent
        HttpTrigger1:  http://localhost:7071/api/hello
```

Ask the agent a question (in a second terminal). Locally no function key is needed:

**macOS/Linux:**
```bash
curl -X POST http://localhost:7071/api/agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Is any device too hot?"}'
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:7071/api/agent -ContentType "application/json" -Body '{"question": "Is any device too hot?"}' | ConvertTo-Json -Depth 5
```

You should get an answer like this (the readings are random, so the numbers differ):
```json
{
  "answer": "Yes - device-02 in the Greenhouse is too hot: 31.7°C exceeds its max of 30.0°C.",
  "steps": [
    {"tool": "list_devices", "input": {}, "result": {"devices": [...]}},
    {"tool": "get_sensor_reading", "input": {"device_id": "device-01"}, "result": {...}},
    {"tool": "get_sensor_reading", "input": {"device_id": "device-02"}, "result": {...}},
    {"tool": "get_sensor_reading", "input": {"device_id": "device-03"}, "result": {...}}
  ]
}
```

Look at the `steps`: the model first listed the devices, then asked for the reading of each one, and only then answered. Try other questions, for example `"What is the humidity in the warehouse?"` or `"Is device-99 OK?"` (an unknown device - watch how the model reacts to the tool's error message). The terminal with `func start` logs every tool call.

If the function answers `Missing settings: ...`, the environment variables aren't set in the terminal where `func start` runs.

### Step 20: Deploy the Agent to Azure

In **Azure Cloud Shell**, add the connection details as **application settings** of your Function App (in the same session as Step 17; set `FUNCTION_APP_NAME` again if needed).

**Option A: Using Bash (recommended)**
```bash
FUNCTION_APP_NAME="func-yourname-12345"  # Your Function App name from Step 10
```
```bash
az functionapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $FUNCTION_APP_NAME \
  --settings \
    AZURE_OPENAI_ENDPOINT=$(az cognitiveservices account show --name $AI_NAME --resource-group $RESOURCE_GROUP --query properties.endpoint --output tsv) \
    AZURE_OPENAI_API_KEY=$(az cognitiveservices account keys list --name $AI_NAME --resource-group $RESOURCE_GROUP --query key1 --output tsv) \
    AZURE_OPENAI_DEPLOYMENT=$MODEL_DEPLOYMENT \
  --output none
```

**Option B: Using PowerShell**
```powershell
$FUNCTION_APP_NAME="func-yourname-12345"  # Your Function App name from Step 10
```
```powershell
$AI_ENDPOINT=$(az cognitiveservices account show --name $AI_NAME --resource-group $RESOURCE_GROUP --query properties.endpoint --output tsv)
$AI_KEY=$(az cognitiveservices account keys list --name $AI_NAME --resource-group $RESOURCE_GROUP --query key1 --output tsv)
az functionapp config appsettings set `
  --resource-group $RESOURCE_GROUP `
  --name $FUNCTION_APP_NAME `
  --settings AZURE_OPENAI_ENDPOINT=$AI_ENDPOINT AZURE_OPENAI_API_KEY=$AI_KEY AZURE_OPENAI_DEPLOYMENT=$MODEL_DEPLOYMENT `
  --output none
```

Deploy the code again from your computer, as in Step 11:
```bash
func azure functionapp publish func-yourname-12345
```

Get the function key of the agent (the same in Bash and PowerShell):
```bash
az functionapp function keys list --resource-group $RESOURCE_GROUP --name $FUNCTION_APP_NAME --function-name AgentTrigger --query default --output tsv
```

Ask the deployed agent - without the key Azure answers `401 Unauthorized`, with the key (`?code=<key>`) you get the answer:

**macOS/Linux:**
```bash
curl -X POST "https://func-yourname-12345.azurewebsites.net/api/agent?code=<function-key>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is any device too hot?"}'
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod -Method Post -Uri "https://func-yourname-12345.azurewebsites.net/api/agent?code=<function-key>" -ContentType "application/json" -Body '{"question": "Is any device too hot?"}' | ConvertTo-Json -Depth 5
```

The tool calls appear in the logs of the function (Step 14).

### Step 21: Explore and Extend the Agent

1. In the [Foundry portal](https://ai.azure.com), open your resource → **Models + endpoints** → `gpt-5.4-mini` → **Metrics**: the requests and the tokens your agent used
2. Change `SYSTEM_PROMPT` in `sensor_tools.py`, for example tell the model to answer in Polish, and test it locally again
3. Add a third tool: write a function in `sensor_tools.py` (for example `get_devices_by_location(location)`), add its definition to `TOOLS` and a branch in `run_tool()`. Then ask a question that needs it - the model finds the new tool from its description

---

## Cleanup

**Don't forget to delete your resources to avoid charges!**

**Option 1: Delete via Azure Portal**

1. Navigate to Azure Portal
2. Go to **Resource Groups**
3. Find `myResourceGroupFunctions`
4. Click **Delete resource group**
5. Type the resource group name to confirm
6. Click **Delete**

**Option 2: Delete via Azure CLI**

**Using Bash:**
```bash
az group delete --name myResourceGroupFunctions --yes --no-wait
```

**Using PowerShell:**
```powershell
az group delete --name myResourceGroupFunctions --yes --no-wait
```

Deleting the resource group also deletes the Foundry resource from Part 5, but Azure keeps it **soft-deleted** for 48 hours (and you can't reuse its name). Purge it to remove it completely (the same in Bash and PowerShell; use your resource's name):
```bash
az cognitiveservices account purge --name ai-iot-agent-<id> --resource-group myResourceGroupFunctions --location uksouth
```

**Option 3: Delete via VS Code**

1. In the Azure Functions extension
2. Right-click your Function App
3. Select **Delete Function App**
4. Confirm deletion

---

## Troubleshooting

### Function fails to start locally

**Issue:** `func start` fails with Python errors

**Solutions:**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check Python version: `python --version` (must be 3.10+)
- Try `pip install azure-functions` directly

### Deployment fails

**Issue:** Deployment to Azure fails

**Solutions:**
- Check Function App name is globally unique
- Ensure you're signed in to Azure in VS Code
- Check you have permissions in the Azure subscription
- Try deleting and recreating the Function App
- Check Azure region supports Python Functions

### Function works locally but fails in Azure

**Issue:** Function runs locally but returns 500 error in Azure

**Solutions:**
- Check Application Insights logs in Azure Portal
- Ensure all dependencies are in `requirements.txt`
- Check the Python runtime version of the Function App (3.13)
- Look for environment-specific issues (file paths, environment variables)
- Enable streaming logs and make a test request

### Cannot see function URL

**Issue:** Function deployed but URL not showing

**Solutions:**
- Wait 2-3 minutes after deployment
- Refresh Azure Portal
- Check deployment completed successfully in VS Code output
- Try `az functionapp function show` command to get URL

### Authentication errors

**Issue:** Function returns 401 Unauthorized

**Solutions:**
- Check authorization level is set to **Anonymous** (for learning)
- For production, use **Function** level and include function key in URL
- Get function key from Azure Portal: Function → Function Keys

---

## Summary and Learning Outcomes

Congratulations! You've created and deployed a serverless function. You learned:

✅ **Serverless Concepts**: Function-as-a-Service (FaaS) and event-driven computing
✅ **Azure Functions**: HTTP triggers, timer triggers, and function anatomy
✅ **Local Development**: Testing functions locally with Azure Functions Core Tools
✅ **VS Code Integration**: Creating and deploying functions using VS Code
✅ **Deployment**: Publishing functions to Azure Cloud
✅ **Monitoring**: Viewing logs and Application Insights
✅ **Configuration**: Using environment variables and app settings
✅ **AI Agents**: A tool-use loop with Azure OpenAI in Foundry, protected by a function key

### Key Azure Functions Concepts

**Triggers**: What starts the function
- HTTP trigger: Responds to HTTP requests
- Timer trigger: Runs on a schedule
- Queue trigger: Processes queue messages
- Blob trigger: Responds to file uploads
- Event Hub trigger: Processes streaming data

**Bindings**: Input/output connections
- Input binding: Gets data from external source
- Output binding: Sends data to external destination
- Examples: Cosmos DB, Blob Storage, Service Bus

**Hosting Plans**:
- **Flex Consumption**: Pay per execution, auto-scale (what we used)
- **Consumption**: The older serverless plan (Linux Consumption is retired on September 30, 2028)
- **Premium**: Pre-warmed instances, VNet integration
- **Dedicated**: Run on App Service plan

### Azure Functions vs Traditional Servers

| Feature | Traditional Server | Azure Functions |
|---------|-------------------|-----------------|
| **Infrastructure** | Manage VMs | Fully managed |
| **Scaling** | Manual configuration | Automatic |
| **Cost** | Always running | Pay per execution |
| **Deployment** | Complex setup | Simple deployment |
| **State** | Stateful | Stateless (by design) |

## Next Steps

- Add authentication to your function (Azure AD, API keys)
- Connect to Cosmos DB or other Azure services
- Create a complete REST API with multiple endpoints
- Implement Durable Functions for long-running workflows
- Add CI/CD with GitHub Actions or Azure DevOps
- Compare with Exercise 11 (complete serverless IoT platform)
- Explore other trigger types (Blob, Queue, Event Hub)
- Learn about Function chaining and orchestrations

## Additional Resources

- [Azure Functions Documentation](https://learn.microsoft.com/en-us/azure/azure-functions/)
- [Azure Functions Python Developer Guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- [Azure Functions Best Practices](https://learn.microsoft.com/en-us/azure/azure-functions/functions-best-practices)
- [Azure Functions Pricing](https://azure.microsoft.com/en-us/pricing/details/functions/)
- [Durable Functions](https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview)
- [Azure Functions on GitHub](https://github.com/Azure/azure-functions-python-library)

---

## Reference: Common Azure Functions CLI Commands

**Local development:**
```bash
# Create new function project
func init --python

# Create new function
func new --name HttpTrigger1 --template "HTTP trigger" --authlevel anonymous

# Start function locally
func start

# Test function
curl http://localhost:7071/api/hello
```

**Deployment:**
```bash
# Deploy to Azure
func azure functionapp publish <function-app-name>

# List function apps
az functionapp list --output table

# Get function URL
az functionapp function show \
  --resource-group <resource-group> \
  --name <function-app-name> \
  --function-name <function-name>

# Stream logs
func azure functionapp logstream <function-app-name>

# Fetch app settings
func azure functionapp fetch-app-settings <function-app-name>
```

**Management:**
```bash
# List functions in app
az functionapp function list \
  --resource-group <resource-group> \
  --name <function-app-name>

# Stop function app
az functionapp stop \
  --resource-group <resource-group> \
  --name <function-app-name>

# Start function app
az functionapp start \
  --resource-group <resource-group> \
  --name <function-app-name>

# Delete function app
az functionapp delete \
  --resource-group <resource-group> \
  --name <function-app-name>
```
