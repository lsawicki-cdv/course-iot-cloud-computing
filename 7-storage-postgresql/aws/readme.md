## Amazon RDS for PostgreSQL - Store IoT Data in a Relational Database

This is the AWS version of the [Azure Database for PostgreSQL exercise](../readme.md).

**Important**: This guide uses **Europe (London)** (`eu-west-2`) as the default region. The DB instance used here (db.t3.micro, single-AZ, 20 GB of General Purpose storage) is Free Tier eligible: 750 hours per month on accounts with the legacy Free Tier, or paid from your Free Tier credits on newer accounts. A publicly accessible DB instance also uses a public IPv4 address, which can cost about $0.005 per hour. Delete all resources at the end of the exercise.

In this exercise, you will set up your own **PostgreSQL** database server in AWS, connect to it from the terminal and from Python, and store IoT sensor readings in it.

In exercise 9 you will use a NoSQL database that stores JSON documents without a fixed structure. PostgreSQL is a **relational (SQL) database**: data lives in tables with a fixed schema (columns and types), and you query it with SQL. It is a good fit when the data has a clear structure and you need to join, filter and aggregate it - for example, average temperature per device.

**Amazon RDS (Relational Database Service) for PostgreSQL** is a managed service (PaaS): AWS runs the server, installs updates, makes backups and monitors it. You only create databases and tables and connect to them.

| Azure | AWS |
|-------|-----|
| Azure Database for PostgreSQL - Flexible Server | Amazon RDS for PostgreSQL |
| Flexible server | DB instance |
| Burstable B1ms (1 vCore, 2 GB RAM), 32 GB storage | db.t3.micro (2 vCPU, 1 GB RAM), 20 GB storage |
| `<server-name>.postgres.database.azure.com` | `<db-instance-id>.<id>.<region>.rds.amazonaws.com` (the endpoint) |
| Firewall rules | Security group (inbound rules for port 5432) |
| "Allow public access from Azure services" (for Cloud Shell) | Inbound rule for the CloudShell public IP address |
| `az postgres flexible-server db create` | `--db-name` when creating the DB instance |
| `psql` in Azure Cloud Shell | `psql` installed in AWS CloudShell |
| Resource group | No direct equivalent - resources are deleted one by one |

### Key concepts

- **DB instance** - your PostgreSQL server, with an address called the **endpoint**. The DB instance identifier must be unique in your account and region. One DB instance can hold many databases
- **DB instance class** - the size of the server. **db.t3.micro** is the Free Tier class
- **Security group** - by default nobody can connect. You allow port 5432 from the public IP address of your computer and from AWS CloudShell
- **Publicly accessible** - the DB instance gets a public IP address, so you can connect from your computer. In production, databases usually stay private and only applications in the same network connect to them
- **Master user** - the server's administrator login and password, which you choose when creating the DB instance
- **SSL/TLS** - RDS for PostgreSQL requires encrypted connections (`sslmode=require`)

### Tested environments
Ubuntu 26.04
Python 3.10+
AWS CloudShell (Bash and PowerShell)

### Steps

1. Find the public IP address of your computer: open https://api.ipify.org in the browser on your computer and save the address. You will allow it in the security group
2. Issue the following commands in **AWS CloudShell** (the terminal icon in the AWS Console's top bar)

   **Option A: Using Bash (recommended)**
   1. Install `psql`, the PostgreSQL terminal client
   ```bash
   sudo dnf install -y postgresql15
   ```
   2. Set the terminal environmental variables. Choose your own admin password: 8-128 characters, without `/`, `'`, `"`, `@` and spaces
   ```bash
      REGION="eu-west-2"  # Change to another region if needed
   ```
   ```bash
      DB_INSTANCE_ID="iot-postgres"
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
   ```bash
      CLOUDSHELL_IP=$(curl -s https://checkip.amazonaws.com)
   ```
   3. Create a security group and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```bash
      SECURITY_GROUP_ID=$(aws ec2 create-security-group \
         --region $REGION \
         --group-name ${DB_INSTANCE_ID}-sg \
         --description "Security group for $DB_INSTANCE_ID" \
         --query GroupId \
         --output text)
   ```
   4. Allow PostgreSQL connections (port 5432) from your computer and from CloudShell
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $SECURITY_GROUP_ID \
         --protocol tcp \
         --port 5432 \
         --cidr $MY_IP/32
   ```
   ```bash
      aws ec2 authorize-security-group-ingress \
         --region $REGION \
         --group-id $SECURITY_GROUP_ID \
         --protocol tcp \
         --port 5432 \
         --cidr $CLOUDSHELL_IP/32
   ```
   5. Create a PostgreSQL DB instance with the `iotdata` database. It takes about 5-10 minutes
   ```bash
      aws rds create-db-instance \
         --region $REGION \
         --db-instance-identifier $DB_INSTANCE_ID \
         --engine postgres \
         --engine-version 16 \
         --db-instance-class db.t3.micro \
         --allocated-storage 20 \
         --storage-type gp2 \
         --master-username $ADMIN_USER \
         --master-user-password "$ADMIN_PASSWORD" \
         --db-name $DATABASE_NAME \
         --vpc-security-group-ids $SECURITY_GROUP_ID \
         --publicly-accessible \
         --no-multi-az \
         --backup-retention-period 1
   ```
   ```bash
      aws rds wait db-instance-available --region $REGION --db-instance-identifier $DB_INSTANCE_ID
   ```
   6. Get the DB instance's endpoint (hostname) and save it to the terminal environmental variable `DB_HOST`. Save it also for later
   ```bash
      DB_HOST=$(aws rds describe-db-instances \
         --region $REGION \
         --db-instance-identifier $DB_INSTANCE_ID \
         --query "DBInstances[0].Endpoint.Address" \
         --output text)
   ```
   ```bash
   echo $DB_HOST
   ```
   7. Connect to the database with `psql` (enter the admin password when asked)
   ```bash
      psql "host=$DB_HOST port=5432 dbname=$DATABASE_NAME user=$ADMIN_USER sslmode=require"
   ```

   **Option B: Using PowerShell**

   Start PowerShell in AWS CloudShell by typing `pwsh`.
   1. Install `psql`, the PostgreSQL terminal client
   ```powershell
   sudo dnf install -y postgresql15
   ```
   2. Set the terminal environmental variables (PowerShell syntax). Choose your own admin password: 8-128 characters, without `/`, `'`, `"`, `@` and spaces
   ```powershell
      $REGION="eu-west-2"  # Change to another region if needed
   ```
   ```powershell
      $DB_INSTANCE_ID="iot-postgres"
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
   ```powershell
      $CLOUDSHELL_IP=$(curl -s https://checkip.amazonaws.com)
   ```
   3. Create a security group and save its ID to the terminal environmental variable `SECURITY_GROUP_ID`
   ```powershell
      $SECURITY_GROUP_ID=$(aws ec2 create-security-group `
         --region $REGION `
         --group-name "$DB_INSTANCE_ID-sg" `
         --description "Security group for $DB_INSTANCE_ID" `
         --query GroupId `
         --output text)
   ```
   4. Allow PostgreSQL connections (port 5432) from your computer and from CloudShell
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $SECURITY_GROUP_ID `
         --protocol tcp `
         --port 5432 `
         --cidr "$MY_IP/32"
   ```
   ```powershell
      aws ec2 authorize-security-group-ingress `
         --region $REGION `
         --group-id $SECURITY_GROUP_ID `
         --protocol tcp `
         --port 5432 `
         --cidr "$CLOUDSHELL_IP/32"
   ```
   5. Create a PostgreSQL DB instance with the `iotdata` database. It takes about 5-10 minutes
   ```powershell
      aws rds create-db-instance `
         --region $REGION `
         --db-instance-identifier $DB_INSTANCE_ID `
         --engine postgres `
         --engine-version 16 `
         --db-instance-class db.t3.micro `
         --allocated-storage 20 `
         --storage-type gp2 `
         --master-username $ADMIN_USER `
         --master-user-password $ADMIN_PASSWORD `
         --db-name $DATABASE_NAME `
         --vpc-security-group-ids $SECURITY_GROUP_ID `
         --publicly-accessible `
         --no-multi-az `
         --backup-retention-period 1
   ```
   ```powershell
      aws rds wait db-instance-available --region $REGION --db-instance-identifier $DB_INSTANCE_ID
   ```
   6. Get the DB instance's endpoint (hostname) and save it to the terminal environmental variable `DB_HOST`. Save it also for later
   ```powershell
      $DB_HOST=$(aws rds describe-db-instances `
         --region $REGION `
         --db-instance-identifier $DB_INSTANCE_ID `
         --query "DBInstances[0].Endpoint.Address" `
         --output text)
   ```
   ```powershell
   $DB_HOST
   ```
   7. Connect to the database with `psql` (enter the admin password when asked)
   ```powershell
      psql "host=$DB_HOST port=5432 dbname=$DATABASE_NAME user=$ADMIN_USER sslmode=require"
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
   2. Set the connection details as environment variables. `psycopg` reads them automatically, so the password is not written in the code. Use your DB instance's endpoint from step 2

   On **macOS/Linux**:
   ```bash
   export PGHOST="<your-endpoint>.rds.amazonaws.com"
   export PGDATABASE="iotdata"
   export PGUSER="iotadmin"
   export PGPASSWORD="<your-password>"
   export PGSSLMODE="require"
   ```
   On **Windows** (PowerShell):
   ```powershell
   $env:PGHOST="<your-endpoint>.rds.amazonaws.com"
   $env:PGDATABASE="iotdata"
   $env:PGUSER="iotadmin"
   $env:PGPASSWORD="<your-password>"
   $env:PGSSLMODE="require"
   ```
   3. Look at `postgresql_sample.py` (in the `7-storage-postgresql` folder - the same file as in the Azure version): it creates the `sensor_readings` table if it doesn't exist, inserts 20 random readings for each of three devices, and prints statistics calculated by SQL queries (`count`, `avg`, `GROUP BY`, `ORDER BY ... LIMIT`)
   4. Run the sample
   ```bash
   python postgresql_sample.py
   ```
   If it fails with a connection timeout, check that the security group allows your current public IP address (step 1)
5. Go back to `psql` in AWS CloudShell (step 2.7) and query the data the Python sample inserted. If CloudShell was restarted and `psql` can't connect, its public IP address has changed: add an inbound rule for the new one (step 2.4)
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
6. Explore the DB instance in the AWS Console (RDS → Databases → `iot-postgres`)
   1. Connectivity & security: the endpoint, the port and the security group
   2. Configuration: the PostgreSQL version, the DB instance class and the storage
   3. Maintenance & backups: the automatic backups and the maintenance window when AWS installs updates
   4. Monitoring: CPU usage, database connections and free storage space
7. Delete the resources (the same commands work in Bash and PowerShell). Deleting the DB instance takes a few minutes
   ```bash
   aws rds delete-db-instance --region $REGION --db-instance-identifier $DB_INSTANCE_ID --skip-final-snapshot --delete-automated-backups
   ```
   ```bash
   aws rds wait db-instance-deleted --region $REGION --db-instance-identifier $DB_INSTANCE_ID
   ```
   ```bash
   aws ec2 delete-security-group --region $REGION --group-id $SECURITY_GROUP_ID
   ```
