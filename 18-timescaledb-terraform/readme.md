## TimescaleDB for IoT Time-Series Data with Terraform

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. This exercise deploys an Azure VM, and your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead of the default region if necessary.

### Learning Objectives
- Understand time-series databases and why they're important for IoT
- Learn about TimescaleDB hypertables for efficient time-series storage
- Implement continuous aggregates for pre-computed metrics
- Use cron jobs to refresh aggregates automatically
- Query time-series data efficiently (last day, week, month, year)
- Deploy infrastructure with Terraform to Azure
- Run databases in Docker containers

### Tested environments
Ubuntu 22.04
Terraform v1.11.0
Docker 24.0+
Python 3.10.12

### Background

#### What is TimescaleDB?
TimescaleDB is a PostgreSQL extension that transforms PostgreSQL into a time-series database. It's designed for storing and analyzing large amounts of time-stamped data from IoT devices, sensors, financial systems, etc.

**Key Features:**
- **Hypertables**: Automatically partition data by time for fast queries
- **Continuous Aggregates**: Pre-computed, automatically updated materialized views
- **Compression**: Reduce storage costs by 90%+
- **SQL Interface**: Use familiar SQL instead of learning new query languages
- **Retention Policies**: Automatically delete old data

#### Why Time-Series Databases for IoT?
IoT devices generate continuous streams of time-stamped data:
- Temperature readings every minute
- Humidity measurements every 30 seconds
- GPS coordinates every 5 seconds
- Power consumption every second

Regular databases struggle with:
- Billions of rows of time-series data
- Complex time-based queries (e.g., "average temperature per hour for last month")
- Storage costs for continuous data

TimescaleDB solves these problems.

#### What are Continuous Aggregates?
Continuous aggregates are automatically maintained materialized views that:
- Pre-compute common metrics (averages, sums, counts)
- Update incrementally as new data arrives
- Make queries extremely fast (query pre-computed results instead of raw data)
- Save compute resources (calculate once, query many times)

**Example:**
Instead of calculating average temperature per hour from millions of rows every time,
continuous aggregate pre-computes it and updates incrementally.

### Architecture

```
IoT Devices → Data Generator → TimescaleDB (Hypertable)
                                      ↓
                              Continuous Aggregates
                              (hourly, daily, monthly)
                                      ↓
                                Cron Jobs (refresh)
                                      ↓
                              REST API ← Clients
```

### Exercise

In this exercise, you will:
1. Use Terraform to deploy an Azure VM
2. Set up TimescaleDB in Docker
3. Create hypertables for IoT sensor data
4. Set up continuous aggregates for different time periods
5. Generate sample IoT data
6. Create a REST API to query data efficiently
7. Set up cron jobs to refresh aggregates
8. Query data for last day, week, month, and year

#### Prerequisites
1. Azure account and Azure CLI installed
2. Terraform installed
3. SSH key for VM access
4. Basic understanding of SQL and Docker

### Steps

#### 1. Deploy Infrastructure with Terraform

Review the Terraform configuration files:
- `main.tf`: Azure VM, networking, security groups
- `variables.tf`: Configuration variables
- `outputs.tf`: VM IP address and connection info
- `docker-setup.sh`: Script to install Docker on the VM

Deploy to Azure:
```bash
cd 18-timescaledb-terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan -out main.tfplan

# Apply
terraform apply main.tfplan
```

Note the VM's public IP address from the output.

#### 2. Connect to the VM

SSH into your Azure VM:
```bash
ssh azureuser@<VM_PUBLIC_IP>
```

Verify Docker is installed:
```bash
docker --version
docker compose version
```

#### 3. Set Up TimescaleDB with Docker Compose

On the VM, clone this repository or copy the files:
```bash
# Option 1: Clone repository
git clone <repository-url>
cd 18-timescaledb-terraform

# Option 2: Use scp to copy files
# From your local machine:
scp -r app/ docker-compose.yml azureuser@<VM_PUBLIC_IP>:~/
```

Start TimescaleDB:
```bash
docker compose up -d
```

Check that containers are running:
```bash
docker compose ps
```

You should see:
- `timescaledb`: Database container
- `api`: REST API container (we'll build this)

#### 4. Initialize the Database

Run the initialization script to create hypertables and continuous aggregates:
```bash
python3 init_database.py
```

This script:
1. Creates `sensor_data` table
2. Converts it to a hypertable partitioned by time
3. Creates continuous aggregates:
   - `sensor_data_hourly`: Average, min, max per hour
   - `sensor_data_daily`: Aggregates per day
   - `sensor_data_monthly`: Aggregates per month
4. Sets up retention policy (optional)

#### 5. Generate Sample IoT Data

Run the data generator to populate the database with sample sensor readings:
```bash
python3 generate_data.py --days 30 --sensors 10 --interval 60
```

Parameters:
- `--days`: Number of days of historical data to generate
- `--sensors`: Number of different sensors
- `--interval`: Seconds between readings per sensor

This creates realistic IoT data:
- Temperature (15-35°C)
- Humidity (30-80%)
- Pressure (980-1020 hPa)
- Timestamps spanning the specified period

#### 6. Understand the Database Schema

**Hypertable: `sensor_data`**
```sql
CREATE TABLE sensor_data (
    time        TIMESTAMPTZ NOT NULL,
    sensor_id   VARCHAR(50) NOT NULL,
    temperature DOUBLE PRECISION,
    humidity    DOUBLE PRECISION,
    pressure    DOUBLE PRECISION
);

SELECT create_hypertable('sensor_data', 'time');
```

**Continuous Aggregate: `sensor_data_hourly`**
```sql
CREATE MATERIALIZED VIEW sensor_data_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    sensor_id,
    AVG(temperature) as avg_temperature,
    MIN(temperature) as min_temperature,
    MAX(temperature) as max_temperature,
    AVG(humidity) as avg_humidity,
    AVG(pressure) as avg_pressure,
    COUNT(*) as reading_count
FROM sensor_data
GROUP BY bucket, sensor_id;
```

#### 7. Set Up Cron Jobs for Aggregate Refresh

Continuous aggregates need to be refreshed to include recent data:

```bash
# Edit crontab
crontab -e

# Add these lines to refresh aggregates every hour
0 * * * * /usr/bin/python3 /home/azureuser/refresh_aggregates.py >> /var/log/refresh_aggregates.log 2>&1
```

The refresh script updates continuous aggregates with new data.

#### 8. Start the REST API

The REST API provides efficient endpoints for querying time-series data:

```bash
cd app
python3 api.py
```

Or use Docker Compose (API container):
```bash
docker compose up -d api
```

The API will be available at `http://<VM_PUBLIC_IP>:5000`

#### 9. Query Data via REST API

**Available Endpoints:**

- `GET /api/sensors` - List all sensors
- `GET /api/sensors/{sensor_id}/current` - Latest reading
- `GET /api/sensors/{sensor_id}/raw?period=1d` - Raw data for period
- `GET /api/sensors/{sensor_id}/hourly?period=1w` - Hourly aggregates
- `GET /api/sensors/{sensor_id}/daily?period=1m` - Daily aggregates
- `GET /api/sensors/{sensor_id}/monthly?period=1y` - Monthly aggregates

**Period formats:**
- `1h` = 1 hour
- `1d` = 1 day
- `1w` = 1 week
- `1m` = 1 month
- `1y` = 1 year

**Examples:**

Get latest reading:
```bash
curl http://<VM_PUBLIC_IP>:5000/api/sensors/sensor_001/current
```

Get hourly averages for last week:
```bash
curl http://<VM_PUBLIC_IP>:5000/api/sensors/sensor_001/hourly?period=1w
```

Get daily aggregates for last month:
```bash
curl http://<VM_PUBLIC_IP>:5000/api/sensors/sensor_001/daily?period=1m
```

Get monthly aggregates for last year:
```bash
curl http://<VM_PUBLIC_IP>:5000/api/sensors/sensor_001/monthly?period=1y
```

#### 10. Test with the Client

From your local machine:
```bash
python3 client_test.py --host <VM_PUBLIC_IP> --port 5000
```

This demonstrates:
- Querying different time periods
- Performance comparison (raw vs aggregates)
- Visualization of query efficiency

#### 11. Understand Query Performance

**Without Continuous Aggregates:**
- Query millions of rows for averages
- Slow response times (seconds)
- High CPU usage

**With Continuous Aggregates:**
- Query pre-computed results
- Fast response times (milliseconds)
- Low CPU usage

**Example:**
```sql
-- Slow: Scan millions of rows
SELECT time_bucket('1 hour', time) AS hour,
       AVG(temperature)
FROM sensor_data
WHERE time > NOW() - INTERVAL '1 month'
GROUP BY hour;

-- Fast: Query pre-computed aggregate
SELECT bucket, avg_temperature
FROM sensor_data_hourly
WHERE bucket > NOW() - INTERVAL '1 month';
```

#### 12. Monitor Database Performance

Connect to TimescaleDB:
```bash
docker exec -it timescaledb psql -U postgres -d iotdata
```

Check hypertable info:
```sql
SELECT * FROM timescaledb_information.hypertables;
```

Check continuous aggregate stats:
```sql
SELECT * FROM timescaledb_information.continuous_aggregates;
```

View data chunks:
```sql
SELECT * FROM timescaledb_information.chunks;
```

Check compression stats (if enabled):
```sql
SELECT * FROM timescaledb_information.compression_settings;
```

### Advanced Features

#### Enable Compression

Reduce storage by 90%+ for older data:
```sql
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sensor_id'
);

-- Compress chunks older than 7 days
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
```

#### Set Retention Policy

Automatically delete data older than 90 days:
```sql
SELECT add_retention_policy('sensor_data', INTERVAL '90 days');
```

#### Create Additional Aggregates

For specific use cases:
```sql
-- Peak hours aggregate
CREATE MATERIALIZED VIEW peak_hours
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS day,
    sensor_id,
    MAX(temperature) as max_temp,
    MIN(temperature) as min_temp,
    MAX(temperature) - MIN(temperature) as temperature_range
FROM sensor_data
GROUP BY day, sensor_id;
```

### Performance Comparison

Test query performance:

**Query 1: Average temperature per hour for last 30 days**
- Without aggregates: ~2-5 seconds (millions of rows)
- With aggregates: ~50-100ms (720 pre-computed rows)
- **50x faster!**

**Query 2: Daily averages for last year**
- Without aggregates: ~10-20 seconds
- With aggregates: ~100-200ms
- **100x faster!**

### Questions to Consider

1. **Why partition by time?**
   - Most queries filter by time range
   - Older data can be compressed or archived
   - Efficient for append-only workloads (IoT data)

2. **How often should aggregates refresh?**
   - Real-time apps: Every minute
   - Analytics: Every hour
   - Reports: Daily
   - Balance freshness vs. compute cost

3. **What's the difference between hypertable and regular table?**
   - Hypertable: Automatically partitioned by time, optimized for time-series queries
   - Regular table: Single partition, slower for large time-series datasets

4. **When to use continuous aggregates vs. real-time queries?**
   - Continuous aggregates: For common, repeated queries
   - Real-time queries: For ad-hoc analysis or recent data

### Cleanup

When finished, destroy the infrastructure:
```bash
# Stop Docker containers on VM
docker compose down

# From your local machine, destroy Terraform resources
terraform plan -destroy -out main.destroy.tfplan
terraform apply main.destroy.tfplan
```

### Additional Resources

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Continuous Aggregates Guide](https://docs.timescale.com/use-timescale/latest/continuous-aggregates/)
- [Hypertables Explained](https://docs.timescale.com/use-timescale/latest/hypertables/)
- [Time-Series Best Practices](https://docs.timescale.com/use-timescale/latest/schema-management/)

### Troubleshooting

**"Cannot connect to database"**
- Check Docker container is running: `docker compose ps`
- Check firewall rules in Azure Network Security Group
- Verify connection string in configuration

**"Continuous aggregate not updating"**
- Check cron job is running: `crontab -l`
- Manually refresh: `CALL refresh_continuous_aggregate('sensor_data_hourly', NULL, NULL);`
- Check logs: `/var/log/refresh_aggregates.log`

**"Queries are slow"**
- Ensure you're querying aggregates, not raw data
- Check if aggregates are up to date
- Consider adding indexes
- Enable compression for old data
