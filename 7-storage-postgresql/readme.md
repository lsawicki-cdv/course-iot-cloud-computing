## Azure Database for PostgreSQL - Store IoT Data in a Relational Database

> Using AWS instead? Follow the [AWS version of this exercise](aws/readme.md).

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. While this guide uses **UK South** as the default region, your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead.

In this exercise, you will set up your own **PostgreSQL** database server in Azure, connect to it from the terminal and from Python, and store IoT sensor readings in it.

In exercise 9 you will use Cosmos DB, a NoSQL database that stores JSON documents without a fixed structure. PostgreSQL is a **relational (SQL) database**: data lives in tables with a fixed schema (columns and types), and you query it with SQL. It is a good fit when the data has a clear structure and you need to join, filter and aggregate it - for example, average temperature per device.

**Azure Database for PostgreSQL - Flexible Server** is a managed service (PaaS): Azure runs the server, installs updates, makes backups and monitors it. You only create databases and tables and connect to them.

### Key concepts

- **Flexible server** - your PostgreSQL server, with the address `<server-name>.postgres.database.azure.com`. The name must be globally unique. One server can hold many databases
- **Compute tier and size** - this exercise uses **Burstable B1ms** (1 vCore, 2 GB RAM) with 32 GB of storage, which is free for 750 hours per month on Azure for Students and free accounts (check "Free services" in the Azure Portal)
- **Firewall rules** - by default nobody can connect. You allow Azure services (so Azure Cloud Shell can connect) and the public IP address of your computer
- **Admin user** - the server's administrator login and password, which you choose when creating the server
- **SSL/TLS** - the server only accepts encrypted connections (`sslmode=require`)

### Tested environments
Ubuntu 26.04
Python 3.10+
Azure Cloud Shell (Bash and PowerShell)

### Steps

1. Find the public IP address of your computer: open https://api.ipify.org in the browser on your computer and save the address. You will allow it in the server's firewall
2. Issue the following commands in **the Azure Cloud Shell**

   **Option A: Using Bash (recommended)**
   1. Set the terminal environmental variables. The server name gets a random number, because it must be globally unique. Choose your own admin password: 8-128 characters, with at least three of: uppercase letters, lowercase letters, digits and symbols
   ```bash
      RESOURCE_GROUP="myResourceGroupPostgreSQL"
   ```
   ```bash
      LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   ```bash
      SERVER_NAME="iot-postgres-$RANDOM"
   ```
   ```bash
      ADMIN_USER="iotadmin"
   ```
   ```bash
      ADMIN_PASSWORD="<your-password>"
   ```
   ```bash
      DATABASE_NAME="iotdata"
   ```
   ```bash
      MY_IP="<your-public-ip>"  # The address from step 1
   ```
   2. Create a resource group using the terminal environmental variables
   ```bash
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a PostgreSQL flexible server. `--public-access 0.0.0.0` allows connections from Azure services, including Azure Cloud Shell. It takes about 5-10 minutes
   ```bash
      az postgres flexible-server create \
         --resource-group $RESOURCE_GROUP \
         --name $SERVER_NAME \
         --location $LOCATION \
         --admin-user $ADMIN_USER \
         --admin-password "$ADMIN_PASSWORD" \
         --tier Burstable \
         --sku-name Standard_B1ms \
         --storage-size 32 \
         --version 16 \
         --public-access 0.0.0.0
   ```
   If it fails with `The location is restricted for provisioning of flexible servers`, delete the resource group and try again with another allowed region.
   4. Create a firewall rule that allows connections from your computer
   ```bash
      az postgres flexible-server firewall-rule create \
         --resource-group $RESOURCE_GROUP \
         --server-name $SERVER_NAME \
         --name allow-my-ip \
         --start-ip-address $MY_IP \
         --end-ip-address $MY_IP
   ```
   5. Create a database for the IoT data
   ```bash
      az postgres flexible-server db create \
         --resource-group $RESOURCE_GROUP \
         --server-name $SERVER_NAME \
         --name $DATABASE_NAME
   ```
   6. Show the server's hostname. Save it - you'll need it later
   ```bash
   echo $SERVER_NAME.postgres.database.azure.com
   ```
   7. Connect to the database with `psql`, the PostgreSQL terminal client (enter the admin password when asked)
   ```bash
      psql "host=$SERVER_NAME.postgres.database.azure.com port=5432 dbname=$DATABASE_NAME user=$ADMIN_USER sslmode=require"
   ```

   **Option B: Using PowerShell**
   1. Set the terminal environmental variables (PowerShell syntax). The server name gets a random number, because it must be globally unique. Choose your own admin password: 8-128 characters, with at least three of: uppercase letters, lowercase letters, digits and symbols
   ```powershell
      $RESOURCE_GROUP="myResourceGroupPostgreSQL"
   ```
   ```powershell
      $LOCATION="uksouth"  # Change to your allowed region if needed
   ```
   ```powershell
      $SERVER_NAME="iot-postgres-$(Get-Random -Maximum 99999)"
   ```
   ```powershell
      $ADMIN_USER="iotadmin"
   ```
   ```powershell
      $ADMIN_PASSWORD="<your-password>"
   ```
   ```powershell
      $DATABASE_NAME="iotdata"
   ```
   ```powershell
      $MY_IP="<your-public-ip>"  # The address from step 1
   ```
   2. Create a resource group using the terminal environmental variables
   ```powershell
   az group create --name $RESOURCE_GROUP --location $LOCATION
   ```
   3. Create a PostgreSQL flexible server. `--public-access 0.0.0.0` allows connections from Azure services, including Azure Cloud Shell. It takes about 5-10 minutes
   ```powershell
      az postgres flexible-server create `
         --resource-group $RESOURCE_GROUP `
         --name $SERVER_NAME `
         --location $LOCATION `
         --admin-user $ADMIN_USER `
         --admin-password $ADMIN_PASSWORD `
         --tier Burstable `
         --sku-name Standard_B1ms `
         --storage-size 32 `
         --version 16 `
         --public-access 0.0.0.0
   ```
   If it fails with `The location is restricted for provisioning of flexible servers`, delete the resource group and try again with another allowed region.
   4. Create a firewall rule that allows connections from your computer
   ```powershell
      az postgres flexible-server firewall-rule create `
         --resource-group $RESOURCE_GROUP `
         --server-name $SERVER_NAME `
         --name allow-my-ip `
         --start-ip-address $MY_IP `
         --end-ip-address $MY_IP
   ```
   5. Create a database for the IoT data
   ```powershell
      az postgres flexible-server db create `
         --resource-group $RESOURCE_GROUP `
         --server-name $SERVER_NAME `
         --name $DATABASE_NAME
   ```
   6. Show the server's hostname. Save it - you'll need it later
   ```powershell
   "$SERVER_NAME.postgres.database.azure.com"
   ```
   7. Connect to the database with `psql`, the PostgreSQL terminal client (enter the admin password when asked)
   ```powershell
      psql "host=$SERVER_NAME.postgres.database.azure.com port=5432 dbname=$DATABASE_NAME user=$ADMIN_USER sslmode=require"
   ```
3. In `psql`, create a table and work with it using SQL (the prompt is `iotdata=>`; run one statement at a time)
   1. Create a table for sensor readings. Every column has a type, and `id` is filled in automatically
   ```sql
   CREATE TABLE sensor_readings (
       id SERIAL PRIMARY KEY,
       device_id TEXT NOT NULL,
       temperature REAL NOT NULL,
       humidity REAL NOT NULL,
       pressure REAL NOT NULL,
       recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   ```
   2. Insert two readings
   ```sql
   INSERT INTO sensor_readings (device_id, temperature, humidity, pressure)
   VALUES ('device-01', 22.5, 45.0, 1013.2), ('device-02', 24.1, 52.3, 1009.8);
   ```
   3. Query the table
   ```sql
   SELECT * FROM sensor_readings;
   ```
   4. List the tables and show the table's structure
   ```sql
   \dt
   ```
   ```sql
   \d sensor_readings
   ```
   5. Leave `psql`
   ```sql
   \q
   ```
4. Connect to the database from Python on your computer (needs Python 3.10+)
   1. Create a virtual environment and install the PostgreSQL driver (`psycopg`)

   On **macOS/Linux**:
   ```bash
   cd 7-storage-postgresql
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   On **Windows** (PowerShell):
   ```powershell
   cd 7-storage-postgresql
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   2. Set the connection details as environment variables. `psycopg` reads them automatically, so the password is not written in the code. Use your server's hostname from step 2

   On **macOS/Linux**:
   ```bash
   export PGHOST="<server-name>.postgres.database.azure.com"
   export PGDATABASE="iotdata"
   export PGUSER="iotadmin"
   export PGPASSWORD="<your-password>"
   export PGSSLMODE="require"
   ```
   On **Windows** (PowerShell):
   ```powershell
   $env:PGHOST="<server-name>.postgres.database.azure.com"
   $env:PGDATABASE="iotdata"
   $env:PGUSER="iotadmin"
   $env:PGPASSWORD="<your-password>"
   $env:PGSSLMODE="require"
   ```
   3. Look at `postgresql_sample.py`: it creates the `sensor_readings` table if it doesn't exist, inserts 20 random readings for each of three devices, and prints statistics calculated by SQL queries (`count`, `avg`, `GROUP BY`, `ORDER BY ... LIMIT`)
   4. Run the sample
   ```bash
   python postgresql_sample.py
   ```
   If it fails with a connection timeout, check that the firewall rule contains your current public IP address (step 1)
5. Go back to `psql` in the Azure Cloud Shell (step 2.7) and query the data the Python sample inserted
   1. Average temperature per device
   ```sql
   SELECT device_id, count(*), round(avg(temperature)::numeric, 1) AS avg_temperature
   FROM sensor_readings
   GROUP BY device_id
   ORDER BY device_id;
   ```
   2. Readings from the last 10 minutes with a temperature above 25 C
   ```sql
   SELECT device_id, temperature, recorded_at
   FROM sensor_readings
   WHERE recorded_at > now() - interval '10 minutes' AND temperature > 25
   ORDER BY recorded_at DESC;
   ```
6. Explore the server in the Azure Portal (Azure Database for PostgreSQL flexible servers → your server)
   1. Overview: the server name (hostname), the PostgreSQL version and the compute size
   2. Networking: the firewall rules you created
   3. Databases: the `iotdata` database
   4. Backup and restore: the automatic backups Azure makes for you
   5. Metrics: CPU usage, active connections and storage used
7. Delete the resource group
   ```bash
   az group delete --name $RESOURCE_GROUP --yes --no-wait
   ```
