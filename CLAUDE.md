# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Teaching material for a university course "IoT & Cloud Computing: Azure" (CDV). It is not one application: each numbered top-level directory (`1-cloud-account` … `18-timescaledb-terraform`) is a self-contained, student-facing exercise. The `readme.md` inside each exercise is the main deliverable; code, scripts and IaC files exist to support the steps it describes. There is no root build, test suite, linter or CI.

## Structure and how exercises relate

Exercises build on each other roughly in this order:

- **IaaS** (2–4): `az` CLI scripts for VMs, scale sets, Docker / Azure Container Instances.
- **PaaS** (5–7): Flask App Service sample (5), IoT Hub + MQTT device simulator and a local Mosquitto broker (6), IoT Central (7, readme only).
- **Storage** (8–9): Blob static website, Cosmos DB Python sample.
- **Serverless** (10–11): 10 is a Python Azure Functions app using the **v2 programming model** (`function_app.py` with decorators). 11 is an end-to-end platform (IoT Hub → Stream Analytics → Cosmos DB → Functions REST API → Vue 3 frontend); its `iot-function-app/` uses the **v1 model** (one folder per function with `function.json` + `__init__.py`). Don't mix the two models within one app.
- **IaC** (12–15): the same kind of infrastructure in Bicep (12 Functions, 13 IoT Hub + Blob routing) and in Terraform (14 VM, 15 IoT Hub + Blob routing). 13 and 15 are intentionally parallel so students can compare Bicep vs Terraform; keep them in sync when changing one (the documented difference is routing: 13 routes on `level="storage"`, 15 routes everything).
- **Security / data** (16–18): X.509 device certificates, JWT-protected Flask REST API, TimescaleDB on a Terraform-provisioned VM with Docker Compose, pgAdmin and a REST API.

Device simulators (`simple_mqtt_device_simulator.py` in 6, `simple_azure_device_simulator.py` in 13/15, `device_simulator_x509.py` in 16) are reused across exercises, which refer back to earlier ones.

## Running things

Everything runs per exercise, from inside its directory, in its own virtualenv:

```bash
cd <exercise-dir>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

- Azure Functions (10, 11): `func start` (Azure Functions Core Tools v4). The root `.vscode/` config (launch/tasks/settings) is wired to debug `10-faas-functions` with the venv at `.venv`.
- Bicep (12, 13): `az deployment group create --resource-group <rg> --template-file main.bicep ...`
- Terraform (14, 15, 18): `terraform init && terraform plan -out main.tfplan && terraform apply main.tfplan`; `terraform destroy` to clean up. State, lock files and plans are gitignored.
- Frontend (`11-serverless-iot-platform/example-frontend`): `npm install`, `npm run dev`, `npm run build`, `npm run lint`, `npm run type-check`. `deploy-frontend.sh` deploys it to Blob static website hosting.
- TimescaleDB (18): `docker compose up -d`, then `init_database.py`, `generate_data.py`, `api.py`, `client_test.py`.

Validating a change usually means deploying to a real Azure subscription; there are no offline tests. When editing IaC, at least run `az bicep build --file main.bicep` or `terraform validate` / `terraform fmt`.

## Conventions for exercise content

- Audience is students on **Azure for Students** subscriptions, which restrict deployments to ~5 allowed regions. Every readme starts with the "Important: check your Policy assignments…" note; defaults use **UK South** (`uksouth`). Keep that note and default when adding exercises.
- Readmes target Ubuntu 22.04/24.04 and Python 3.10+, and list a "Tested Environments" section.
- Shell steps are given for Azure Cloud Shell in two variants: **Option A: Bash (recommended)** and **Option B: PowerShell** (backtick line continuation). When changing a command in a readme, update both variants.
- `az` CLI scripts follow the same pattern: `#!/bin/bash`, a `# Variables` block of UPPER_CASE names, then commented `az` steps.
- Resource names in Bicep/Terraform are often made globally unique with a random/`uniqueString` suffix; keep that when adding resources such as storage accounts or IoT Hubs.
- **AWS variants** live in an `aws/` subfolder of the exercise (`<exercise>/aws/readme.md` plus scripts), mirroring the Azure readme step for step: a service-mapping table at the top, `eu-west-2` (London) as the counterpart of UK South, and the same Bash/PowerShell options run in AWS CloudShell. The Azure readme only gets a link to it at the top. Shared files (e.g. `vm.sh`) stay in the exercise root. Students use personal AWS accounts (credit card, Free Tier credits; no AWS Academy), so AWS variants must use only Free Tier eligible services and sizes; where a service isn't covered, say so in the readme and pick the cheapest option or flag it to the instructor. So far `1-cloud-account` and `2-iaas` have one. When adding one, also add the exercise to the "Azure or AWS" list in the root `readme.md`.
- Secrets (`local.settings.json`, `.env`, `appsettings.json`, certificates) are gitignored; examples ship as `.env.example`. `10-faas-functions/local.settings.json` is tracked anyway, but it holds only local Azurite settings and no secrets.
- Commit messages are short imperative sentences that name the exercise, e.g. "Fix TLS version for the IoT Hub in exercise 13th".
