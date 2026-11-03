### AWS App Runner and Elastic Beanstalk - Deploy a Python (Flask) web app

This is the AWS version of the [Azure App Service task](../readme.md).

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. **App Runner (Option A) is not in the Free Tier**: on accounts created after July 2025 it is paid from your Free Tier credits, on older accounts you pay the prices below (a few cents for this task). Elastic Beanstalk (Option B) itself is free; you pay only for the resources it creates, which stay within the Free Tier here. Delete all resources at the end of the task.

In this exercise, you will deploy a small Python web app to a Platform as a Service (PaaS). In exercises 2-4 you created and configured virtual machines yourself (IaaS). With PaaS you only give AWS your code: it creates the servers, installs Python and your packages, starts the app and gives it an address.

AWS has two services for this, and you can try both:
- **Option A: AWS App Runner** - fully managed, like App Service: it builds the code from your GitHub repository and gives it an HTTPS address. You never see the servers
- **Option B: AWS Elastic Beanstalk** - deploys the code from the terminal, like `az webapp up`, onto an EC2 virtual machine that it creates and manages for you. You can still see (and connect to) that virtual machine

The app is the same Flask sample as in the Azure version:
- `app.py` - the Flask app with two pages: `/` shows a form, `/hello` greets the name sent from the form
- `templates/` - the HTML pages (Jinja templates)
- `static/` - Bootstrap CSS, images and the favicon
- `requirements.txt` - the Python packages: Flask and gunicorn (the production web server that runs the app)

| Azure App Service | Option A: App Runner | Option B: Elastic Beanstalk |
|-------------------|----------------------|-----------------------------|
| App Service plan (F1) | Instance size (0.25 vCPU, 0.5 GB) | EC2 instance (t3.micro) |
| Web App | App Runner service | Elastic Beanstalk application + environment |
| `az webapp up` | Service built from your GitHub fork | `eb init` + `eb create` |
| Redeploy with `az webapp up` | Push to GitHub, then "Deploy" | `eb deploy` |
| Startup command (gunicorn, detected automatically) | `apprunner.yaml` | `Procfile` |
| `https://<app-name>.azurewebsites.net` | `https://<id>.<region>.awsapprunner.com` | `http://<env-name>.<id>.<region>.elasticbeanstalk.com` (HTTP only) |
| `az webapp log tail` | "Logs" tab in the Console | `eb logs` |
| Resource group | Delete the service | `eb terminate` |
| Free Tier (F1) | **No** - about $0.02 per hour while handling requests and $0.0035 per hour while idle, plus $0.005 per build minute | **Yes** - one t3.micro, no load balancer |

### Key concepts

- **Build on deployment** - both services detect the Python app and install `requirements.txt`, but unlike App Service they need to be told how to start it: App Runner reads `apprunner.yaml`, Elastic Beanstalk reads `Procfile`
- **App Runner service** - your app with its build settings, size and address. App Runner scales the number of instances automatically, and when there are no requests it keeps the app in memory but doesn't charge for CPU
- **Elastic Beanstalk application and environment** - the application holds the uploaded versions of your code; an environment runs one version on EC2 virtual machines (here a single one, without a load balancer) behind an nginx proxy

### Tested environments
Ubuntu 22.04
Python 3.10.12
AWS CloudShell (Bash and PowerShell)

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
2. Deploy the app with Option A, Option B or both

#### Option A: AWS App Runner

App Runner builds the app from a GitHub repository, so you need a GitHub account and your own copy (fork) of the course repository.

1. Fork the course repository: open https://github.com/lsawicki-cdv/course-iot-cloud-computing and click "Fork"
2. Look at the `5-paas-web-app/apprunner.yaml` file in your fork. It tells App Runner how to build and start the app:
   - `runtime: python311` - the managed Python 3.11 runtime
   - `pip3 install -r requirements.txt` - installs Flask and gunicorn (in the build and again before the app starts, because the Python 3.11 runtime doesn't keep packages installed during the build)
   - `gunicorn --bind 0.0.0.0:8080 app:app` - starts the `app` object from `app.py` on port 8080
   - `PYTHONUNBUFFERED=1` - makes Python write the `print` messages to the logs straight away, instead of keeping them in a buffer
3. Create the App Runner service in the AWS Console: https://console.aws.amazon.com/apprunner/home#/create
   1. Region: Europe (London) (or another region), selected in the top-right corner of the Console
   2. Repository type: Source code repository, Provider: GitHub
   3. GitHub connection: "Add new", sign in to GitHub, and install the "AWS Connector for GitHub" app for your fork
   4. Repository: your fork, Branch: `main`, Source directory: `/5-paas-web-app`
   5. Deployment trigger: Manual (automatic deployment on every push costs $1 per month)
   6. Click "Next". Configuration file: "Use a configuration file" (`apprunner.yaml`)
   7. Click "Next". Service name: `flask-webapp`, Virtual CPU: 0.25 vCPU, Virtual memory: 0.5 GB
   8. Click "Next", then "Create & deploy"
4. Wait until the status is "Running" (5-10 minutes). The "Logs" tab shows the build ("Deployment logs") and the app's output ("Application logs")
5. Open the "Default domain" URL (`https://....awsapprunner.com`) in the browser, enter your name and click "Say Hello". The `print` messages from `app.py` appear in the "Application logs"
6. Check the service from **AWS CloudShell** (the terminal icon in the AWS Console's top bar)

   **Bash:**
   1. Save the service's ARN to the terminal environmental variable `SERVICE_ARN`
   ```bash
      SERVICE_ARN=$(aws apprunner list-services \
         --region eu-west-2 \
         --query "ServiceSummaryList[?ServiceName=='flask-webapp'].ServiceArn" \
         --output text)
   ```
   2. Show the service's status, address and size
   ```bash
      aws apprunner describe-service \
         --region eu-west-2 \
         --service-arn $SERVICE_ARN \
         --query "Service.{Status:Status,Url:ServiceUrl,Cpu:InstanceConfiguration.Cpu,Memory:InstanceConfiguration.Memory}" \
         --output table
   ```

   **PowerShell** (start it by typing `pwsh`):
   1. Save the service's ARN to the terminal environmental variable `SERVICE_ARN`
   ```powershell
      $SERVICE_ARN=$(aws apprunner list-services `
         --region eu-west-2 `
         --query "ServiceSummaryList[?ServiceName=='flask-webapp'].ServiceArn" `
         --output text)
   ```
   2. Show the service's status, address and size
   ```powershell
      aws apprunner describe-service `
         --region eu-west-2 `
         --service-arn $SERVICE_ARN `
         --query "Service.{Status:Status,Url:ServiceUrl,Cpu:InstanceConfiguration.Cpu,Memory:InstanceConfiguration.Memory}" `
         --output table
   ```
7. Change the app: in your fork on GitHub, edit the `<h1>` text in `5-paas-web-app/templates/index.html` (e.g. `Welcome to AWS App Runner`) and commit the change
8. Redeploy: click "Deploy" in the App Runner service, or run in CloudShell (the same in Bash and PowerShell)
   ```bash
   aws apprunner start-deployment --region eu-west-2 --service-arn $SERVICE_ARN
   ```
   Wait until the status is "Running" again and refresh the page
9. Explore the service in the AWS Console (App Runner → Services → `flask-webapp`)
   1. Configuration: the source directory, the build and start commands from `apprunner.yaml`, and the instance size
   2. Activity: the deployments you made
   3. Metrics: requests, response times and the number of active instances
   4. Configuration → Auto scaling: how many instances App Runner may start under load
10. Delete the resources
    1. Delete the service (the same in Bash and PowerShell), or use App Runner → Services → `flask-webapp` → "Actions" → "Delete"
    ```bash
    aws apprunner delete-service --region eu-west-2 --service-arn $SERVICE_ARN
    ```
    2. Delete the GitHub connection: App Runner → GitHub connections → select your connection → "Delete"

#### Option B: AWS Elastic Beanstalk

1. Issue the following commands in **AWS CloudShell** (the terminal icon in the AWS Console's top bar). Apart from step 2, the commands are the same in Bash and PowerShell (start PowerShell by typing `pwsh`)
   1. Install the Elastic Beanstalk CLI
   ```bash
   pip3 install --user awsebcli
   ```
   2. Add the folder with the `eb` command to the `PATH`

   Bash:
   ```bash
   export PATH=$PATH:~/.local/bin
   ```
   PowerShell:
   ```powershell
   $env:PATH += ":$HOME/.local/bin"
   ```
   3. Download the course repository and copy the Flask app to a new folder. The copy is outside git on purpose: inside a git repository `eb deploy` uploads the last commit instead of the files you changed
   ```bash
   git clone --depth 1 https://github.com/lsawicki-cdv/course-iot-cloud-computing.git
   ```
   ```bash
   cp -r course-iot-cloud-computing/5-paas-web-app ~/flask-webapp
   ```
   ```bash
   cd ~/flask-webapp
   ```
   4. Create a `Procfile`, which tells Elastic Beanstalk how to start the app (gunicorn listens on port 8000, where Elastic Beanstalk's nginx proxy expects it)
   ```bash
   echo "web: gunicorn app:app" > Procfile
   ```
   5. Create the Elastic Beanstalk application for Python 3.11 (change the region if needed)
   ```bash
   eb init flask-webapp --platform python-3.11 --region eu-west-2
   ```
   6. Create an environment and deploy the app. `--single` creates one virtual machine without a load balancer, which keeps it in the Free Tier. `PYTHONUNBUFFERED=1` makes Python write the `print` messages to the log straight away, instead of keeping them in a buffer. It takes about 5 minutes
   ```bash
   eb create flask-webapp-env --single --instance_type t3.micro --envvars PYTHONUNBUFFERED=1
   ```
   7. Show the environment's status. The `CNAME` line is the app's address
   ```bash
   eb status
   ```
2. Open `http://<CNAME>` in the browser, enter your name and click "Say Hello"
3. Show the app's logs. The `print` messages from `app.py` are in `web.stdout.log`
   ```bash
   eb logs
   ```
4. Change the app: edit the `<h1>` text in `templates/index.html` (e.g. `Welcome to AWS Elastic Beanstalk`) and redeploy it
   ```bash
   nano templates/index.html
   ```
   ```bash
   eb deploy
   ```
5. Refresh the page in the browser
6. Explore the environment in the AWS Console (Elastic Beanstalk → Environments → `flask-webapp-env`)
   1. Overview: the health, the platform (Python 3.11 on Amazon Linux 2023) and the running version
   2. Events: what `eb create` and `eb deploy` did, step by step
   3. Configuration → Capacity: the "Single instance" environment type and the t3.micro instance type
   4. EC2 → Instances: the virtual machine Elastic Beanstalk created for you. Unlike App Runner, it's visible and you could connect to it
   5. Applications → `flask-webapp` → Application versions: every version you deployed
7. Delete the environment and the application (it takes a few minutes)
   ```bash
   eb terminate flask-webapp-env --all --force
   ```
   Elastic Beanstalk keeps the uploaded app versions in an S3 bucket named `elasticbeanstalk-eu-west-2-<account-id>`. They take little space, but you can delete the bucket in the S3 Console.

The sample app comes from [Azure-Samples/msdocs-python-flask-webapp-quickstart](https://github.com/Azure-Samples/msdocs-python-flask-webapp-quickstart) (MIT license, see `LICENSE.md`).
