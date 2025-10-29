#!/usr/bin/env python3
"""
TimescaleDB Database Initialization Script

This script creates:
1. Hypertable for sensor data
2. Continuous aggregates (hourly, daily, monthly)
3. Refresh policies for automatic updates
4. Optional: Retention and compression policies
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys


# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'iotdata',
    'user': 'postgres',
    'password': 'postgres'
}


def connect_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def create_hypertable(conn):
    """Create sensor_data table and convert to hypertable."""
    print("Creating sensor_data hypertable...")

    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            time        TIMESTAMPTZ NOT NULL,
            sensor_id   VARCHAR(50) NOT NULL,
            temperature DOUBLE PRECISION,
            humidity    DOUBLE PRECISION,
            pressure    DOUBLE PRECISION
        );
    """)

    # Convert to hypertable (if not already)
    try:
        cursor.execute("""
            SELECT create_hypertable('sensor_data', 'time',
                if_not_exists => TRUE,
                chunk_time_interval => INTERVAL '1 day'
            );
        """)
        print("✓ Hypertable created successfully")
    except Exception as e:
        print(f"  Note: {e}")

    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS sensor_data_sensor_id_time_idx
        ON sensor_data (sensor_id, time DESC);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS sensor_data_time_idx
        ON sensor_data (time DESC);
    """)

    conn.commit()
    cursor.close()
    print("✓ Indexes created")


def create_continuous_aggregates(conn):
    """Create continuous aggregates for different time periods."""
    print("\nCreating continuous aggregates...")

    cursor = conn.cursor()

    # Hourly aggregate
    print("  Creating hourly aggregate...")
    cursor.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 hour', time) AS bucket,
            sensor_id,
            AVG(temperature) as avg_temperature,
            MIN(temperature) as min_temperature,
            MAX(temperature) as max_temperature,
            AVG(humidity) as avg_humidity,
            MIN(humidity) as min_humidity,
            MAX(humidity) as max_humidity,
            AVG(pressure) as avg_pressure,
            COUNT(*) as reading_count
        FROM sensor_data
        GROUP BY bucket, sensor_id
        WITH NO DATA;
    """)
    print("    ✓ Hourly aggregate created")

    # Daily aggregate
    print("  Creating daily aggregate...")
    cursor.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_daily
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 day', time) AS bucket,
            sensor_id,
            AVG(temperature) as avg_temperature,
            MIN(temperature) as min_temperature,
            MAX(temperature) as max_temperature,
            AVG(humidity) as avg_humidity,
            MIN(humidity) as min_humidity,
            MAX(humidity) as max_humidity,
            AVG(pressure) as avg_pressure,
            COUNT(*) as reading_count
        FROM sensor_data
        GROUP BY bucket, sensor_id
        WITH NO DATA;
    """)
    print("    ✓ Daily aggregate created")

    # Monthly aggregate
    print("  Creating monthly aggregate...")
    cursor.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_monthly
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 month', time) AS bucket,
            sensor_id,
            AVG(temperature) as avg_temperature,
            MIN(temperature) as min_temperature,
            MAX(temperature) as max_temperature,
            AVG(humidity) as avg_humidity,
            MIN(humidity) as min_humidity,
            MAX(humidity) as max_humidity,
            AVG(pressure) as avg_pressure,
            COUNT(*) as reading_count
        FROM sensor_data
        GROUP BY bucket, sensor_id
        WITH NO DATA;
    """)
    print("    ✓ Monthly aggregate created")

    conn.commit()
    cursor.close()


def create_refresh_policies(conn):
    """Create policies to automatically refresh continuous aggregates."""
    print("\nCreating refresh policies...")

    cursor = conn.cursor()

    # Hourly aggregate: refresh every hour, looking at last 2 hours
    try:
        cursor.execute("""
            SELECT add_continuous_aggregate_policy('sensor_data_hourly',
                start_offset => INTERVAL '2 hours',
                end_offset => INTERVAL '1 minute',
                schedule_interval => INTERVAL '1 hour',
                if_not_exists => TRUE
            );
        """)
        print("  ✓ Hourly refresh policy created (runs every hour)")
    except Exception as e:
        print(f"    Note: {e}")

    # Daily aggregate: refresh every day, looking at last 3 days
    try:
        cursor.execute("""
            SELECT add_continuous_aggregate_policy('sensor_data_daily',
                start_offset => INTERVAL '3 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 day',
                if_not_exists => TRUE
            );
        """)
        print("  ✓ Daily refresh policy created (runs every day)")
    except Exception as e:
        print(f"    Note: {e}")

    # Monthly aggregate: refresh every day, looking at last 2 months
    try:
        cursor.execute("""
            SELECT add_continuous_aggregate_policy('sensor_data_monthly',
                start_offset => INTERVAL '2 months',
                end_offset => INTERVAL '1 day',
                schedule_interval => INTERVAL '1 day',
                if_not_exists => TRUE
            );
        """)
        print("  ✓ Monthly refresh policy created (runs every day)")
    except Exception as e:
        print(f"    Note: {e}")

    conn.commit()
    cursor.close()


def create_optional_policies(conn):
    """Create optional compression and retention policies."""
    print("\nOptional policies (commented out by default):")

    cursor = conn.cursor()

    # Compression policy (uncomment to enable)
    print("  • Compression: Would compress data older than 7 days")
    print("    Uncomment in script to enable")
    # cursor.execute("""
    #     ALTER TABLE sensor_data SET (
    #         timescaledb.compress,
    #         timescaledb.compress_segmentby = 'sensor_id'
    #     );
    # """)
    # cursor.execute("""
    #     SELECT add_compression_policy('sensor_data', INTERVAL '7 days');
    # """)

    # Retention policy (uncomment to enable)
    print("  • Retention: Would delete data older than 90 days")
    print("    Uncomment in script to enable")
    # cursor.execute("""
    #     SELECT add_retention_policy('sensor_data', INTERVAL '90 days');
    # """)

    cursor.close()


def verify_setup(conn):
    """Verify that everything was created successfully."""
    print("\n" + "=" * 60)
    print("Verifying setup...")
    print("=" * 60)

    cursor = conn.cursor()

    # Check hypertable
    cursor.execute("""
        SELECT * FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'sensor_data';
    """)
    hypertable = cursor.fetchone()
    if hypertable:
        print("✓ Hypertable: sensor_data exists")
    else:
        print("✗ Hypertable: sensor_data not found!")

    # Check continuous aggregates
    cursor.execute("""
        SELECT view_name FROM timescaledb_information.continuous_aggregates
        ORDER BY view_name;
    """)
    aggregates = cursor.fetchall()
    if aggregates:
        print(f"✓ Continuous aggregates: {len(aggregates)} created")
        for agg in aggregates:
            print(f"    - {agg[0]}")
    else:
        print("✗ No continuous aggregates found!")

    # Check refresh policies
    cursor.execute("""
        SELECT COUNT(*) FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_refresh_continuous_aggregate';
    """)
    policies = cursor.fetchone()[0]
    print(f"✓ Refresh policies: {policies} active")

    cursor.close()


def main():
    """Main function to initialize the database."""
    print("=" * 60)
    print("TimescaleDB Initialization Script")
    print("=" * 60)
    print()

    # Connect to database
    print("Connecting to database...")
    conn = connect_db()
    print("✓ Connected successfully")
    print()

    try:
        # Create hypertable
        create_hypertable(conn)

        # Create continuous aggregates
        create_continuous_aggregates(conn)

        # Create refresh policies
        create_refresh_policies(conn)

        # Create optional policies
        create_optional_policies(conn)

        # Verify setup
        verify_setup(conn)

        print()
        print("=" * 60)
        print("Database initialization completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Run: python3 generate_data.py --days 30 --sensors 10")
        print("  2. Run: python3 app/api.py")
        print("  3. Test: curl http://localhost:5000/api/sensors")
        print()

    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
