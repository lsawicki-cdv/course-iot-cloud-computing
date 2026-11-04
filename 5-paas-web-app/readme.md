### Azure App Service - Deploy a Python (Flask) web app

> Using AWS instead? Follow the [AWS version of this task](aws/readme.md).

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

In this exercise, you will deploy a small Python web app to **Azure App Service**, a Platform as a Service (PaaS). In exercises 2-4 you created and configured virtual machines yourself (IaaS). With PaaS you only give Azure your code: it creates the servers, installs Python and your packages, starts the app and gives it an HTTPS address.

The app is the Flask sample from the Microsoft quickstart [Deploy a Python (Django or Flask) web app to Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-python):
- `app.py` - the Flask app with two pages: `/` shows a form, `/hello` greets the name sent from the form
- `templates/` - the HTML pages (Jinja templates)
- `static/` - Bootstrap CSS, images and the favicon
- `requirements.txt` - the Python packages: Flask and gunicorn (the production web server App Service uses to run the app)

### Key concepts

- **App Service plan** - the compute (virtual machines) your app runs on, and its price tier. The **F1 (Free)** tier used here is free, but it has limits (60 CPU minutes per day, no custom domains with SSL, the app sleeps when idle)
- **Web App** - your app in the plan, with the address `https://<app-name>.azurewebsites.net`. The name must be globally unique
- **Build on deployment** - App Service (its build system, Oryx) detects `requirements.txt`, installs the packages, finds `app.py` and starts it with gunicorn. You don't write a startup command

### Tested environments
Ubuntu 26.04
Python 3.10+
Azure Cloud Shell (Bash and PowerShell)

### Steps

1. Run the app locally (optional, needs Python 3.10+)

   On **macOS/Linux**:
   ```bash
   cd 5-paas-web-app
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   flask run
   ```
   On **Windows** (PowerShell):
   ```powershell
   cd 5-paas-web-app
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   flask run
   ```
   Open http://127.0.0.1:5000 in the browser, enter your name and click "Say Hello". Stop the app with `Ctrl+C`
2. Issue the following commands in **the Azure Cloud Shell**

   **Option A: Using Bash (recommended)**
   1. Download the course repository and go to the app's folder
   ```bash
   git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
   ```
   ```bash
   cd course-iot-cloud-computing/5-paas-web-app
   ```
   2. Set the terminal environmental variables. The app name gets a random number, because it must be globally unique
   ```bash
      RESOURCE_GROUP="myResourceGroupWebApp"
   ```
   ```bash
      LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   ```bash
      APP_NAME="flask-webapp-$RANDOM"
   ```
   3. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   4. Create the App Service plan and the Web App, and deploy the code from the current folder (it takes a few minutes)
   ```bash
      az webapp up \
         --resource-group $RESOURCE_GROUP \
         --location $LOCATION \
         --name $APP_NAME \
         --runtime PYTHON:3.11 \
         --sku F1
   ```
   5. Check connection to the web app
   ```bash
      curl --connect-timeout 30 https://$APP_NAME.azurewebsites.net
   ```
   6. Turn on the app's logs and stream them to the terminal. Open the app in the browser (`https://<APP_NAME>.azurewebsites.net`), send the form and watch the `print` messages from `app.py`. Stop the stream with `Ctrl+C`
   ```bash
      az webapp log config \
         --resource-group $RESOURCE_GROUP \
         --name $APP_NAME \
         --docker-container-logging filesystem
   ```
   ```bash
      az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME
   ```
   7. Change the app: edit the `<h1>` text in `templates/index.html` (e.g. `Welcome to Azure App Service`) and save the file
   ```bash
   nano templates/index.html
   ```
   8. Redeploy the app with the same command and refresh the page in the browser
   ```bash
      az webapp up \
         --resource-group $RESOURCE_GROUP \
         --location $LOCATION \
         --name $APP_NAME \
         --runtime PYTHON:3.11 \
         --sku F1
   ```

   **Option B: Using PowerShell**
   1. Download the course repository and go to the app's folder
   ```powershell
   git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
   ```
   ```powershell
   cd course-iot-cloud-computing/5-paas-web-app
   ```
   2. Set the terminal environmental variables (PowerShell syntax). The app name gets a random number, because it must be globally unique
   ```powershell
      $RESOURCE_GROUP="myResourceGroupWebApp"
   ```
   ```powershell
      $LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   ```powershell
      $APP_NAME="flask-webapp-$(Get-Random -Maximum 99999)"
   ```
   3. Create a resource group using the terminal environmental variables
   ```powershell
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   4. Create the App Service plan and the Web App, and deploy the code from the current folder (it takes a few minutes)
   ```powershell
      az webapp up `
         --resource-group $RESOURCE_GROUP `
         --location $LOCATION `
         --name $APP_NAME `
         --runtime PYTHON:3.11 `
         --sku F1
   ```
   5. Check connection to the web app
   ```powershell
      curl --connect-timeout 30 https://$APP_NAME.azurewebsites.net
   ```
   6. Turn on the app's logs and stream them to the terminal. Open the app in the browser (`https://<APP_NAME>.azurewebsites.net`), send the form and watch the `print` messages from `app.py`. Stop the stream with `Ctrl+C`
   ```powershell
      az webapp log config `
         --resource-group $RESOURCE_GROUP `
         --name $APP_NAME `
         --docker-container-logging filesystem
   ```
   ```powershell
      az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME
   ```
   7. Change the app: edit the `<h1>` text in `templates/index.html` (e.g. `Welcome to Azure App Service`) and save the file
   ```powershell
   nano templates/index.html
   ```
   8. Redeploy the app with the same command and refresh the page in the browser
   ```powershell
      az webapp up `
         --resource-group $RESOURCE_GROUP `
         --location $LOCATION `
         --name $APP_NAME `
         --runtime PYTHON:3.11 `
         --sku F1
   ```
3. Explore the Web App in the Azure Portal (App Services → your app)
   1. Overview: the default domain, the App Service plan and its pricing tier (F1)
   2. Deployment Center → Logs: the deployments you made with `az webapp up`
   3. Log stream: the same logs as `az webapp log tail`
   4. Configuration → General settings: the Python version and the (empty) startup command, which means App Service detected gunicorn and `app.py` itself
   5. Scale up (App Service plan): the other price tiers and what they add
4. Delete the resource group
   ```bash
   az group delete --name $RESOURCE_GROUP --yes --no-wait
   ```

The sample app comes from [Azure-Samples/msdocs-python-flask-webapp-quickstart](https://github.com/Azure-Samples/msdocs-python-flask-webapp-quickstart) (MIT license, see `LICENSE.md`).
