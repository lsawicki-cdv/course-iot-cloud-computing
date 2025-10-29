#!/usr/bin/env python3
"""
IoT Data Generator for TimescaleDB

Generates realistic sensor data for testing:
- Temperature (15-35°C with daily variation)
- Humidity (30-80%)
- Pressure (980-1020 hPa)
- Multiple sensors over configurable time period
"""

import psycopg2
import argparse
from datetime import datetime, timedelta
import random
import sys
import time


# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'iotdata',
    'user': 'postgres',
    'password': 'postgres'
}


def generate_temperature(base_time, sensor_id):
    """
    Generate realistic temperature with daily variation.

    Args:
        base_time: datetime object
        sensor_id: sensor identifier

    Returns:
        Temperature in Celsius
    """
    # Base temperature varies by sensor
    sensor_offset = hash(sensor_id) % 5
    base_temp = 20 + sensor_offset

    # Daily variation (warmer during day, cooler at night)
    hour = base_time.hour
    daily_variation = 5 * abs((hour - 14) / 12 - 1)  # Peak at 2 PM

    # Random noise
    noise = random.uniform(-2, 2)

    temperature = base_temp + daily_variation + noise
    return round(temperature, 2)


def generate_humidity(temperature):
    """
    Generate humidity that correlates negatively with temperature.

    Args:
        temperature: Current temperature

    Returns:
        Humidity percentage
    """
    # Higher temperature = lower humidity (generally)
    base_humidity = 70 - (temperature - 20) * 1.5

    # Random variation
    noise = random.uniform(-10, 10)

    humidity = max(30, min(80, base_humidity + noise))
    return round(humidity, 2)


def generate_pressure():
    """
    Generate atmospheric pressure.

    Returns:
        Pressure in hPa
    """
    # Standard pressure with random variation
    pressure = 1013.25 + random.uniform(-20, 20)
    return round(pressure, 2)


def generate_sensor_reading(timestamp, sensor_id):
    """
    Generate a complete sensor reading.

    Args:
        timestamp: datetime object
        sensor_id: sensor identifier

    Returns:
        Dictionary with sensor data
    """
    temperature = generate_temperature(timestamp, sensor_id)
    humidity = generate_humidity(temperature)
    pressure = generate_pressure()

    return {
        'time': timestamp,
        'sensor_id': sensor_id,
        'temperature': temperature,
        'humidity': humidity,
        'pressure': pressure
    }


def insert_batch(conn, data_batch):
    """
    Insert a batch of readings into the database.

    Args:
        conn: Database connection
        data_batch: List of sensor readings
    """
    cursor = conn.cursor()

    # Prepare data for batch insert
    values = [(
        d['time'],
        d['sensor_id'],
        d['temperature'],
        d['humidity'],
        d['pressure']
    ) for d in data_batch]

    # Execute batch insert
    cursor.executemany("""
        INSERT INTO sensor_data (time, sensor_id, temperature, humidity, pressure)
        VALUES (%s, %s, %s, %s, %s)
    """, values)

    conn.commit()
    cursor.close()


def generate_data(days, num_sensors, interval_seconds, batch_size=1000):
    """
    Generate historical IoT data.

    Args:
        days: Number of days of historical data
        num_sensors: Number of different sensors
        interval_seconds: Seconds between readings per sensor
        batch_size: Number of readings to insert at once
    """
    print("=" * 60)
    print("IoT Data Generator")
    print("=" * 60)
    print(f"  Days of data: {days}")
    print(f"  Number of sensors: {num_sensors}")
    print(f"  Interval: {interval_seconds} seconds")
    print(f"  Batch size: {batch_size} readings")
    print()

    # Calculate total readings
    readings_per_sensor = (days * 24 * 3600) // interval_seconds
    total_readings = readings_per_sensor * num_sensors

    print(f"  Total readings to generate: {total_readings:,}")
    print()

    # Connect to database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected to database")
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        sys.exit(1)

    # Generate sensor IDs
    sensor_ids = [f"sensor_{i:03d}" for i in range(1, num_sensors + 1)]

    # Start time (days ago)
    start_time = datetime.now() - timedelta(days=days)

    print(f"✓ Generating data from {start_time} to {datetime.now()}")
    print()

    try:
        data_batch = []
        count = 0
        last_print_count = 0

        # Generate data for each sensor
        for sensor_id in sensor_ids:
            current_time = start_time

            while current_time < datetime.now():
                # Generate reading
                reading = generate_sensor_reading(current_time, sensor_id)
                data_batch.append(reading)
                count += 1

                # Insert batch when it reaches batch_size
                if len(data_batch) >= batch_size:
                    insert_batch(conn, data_batch)
                    data_batch = []

                    # Print progress every 10000 readings
                    if count - last_print_count >= 10000:
                        progress = (count / total_readings) * 100
                        print(f"  Progress: {count:,} / {total_readings:,} ({progress:.1f}%)")
                        last_print_count = count

                # Move to next reading time
                current_time += timedelta(seconds=interval_seconds)

        # Insert remaining batch
        if data_batch:
            insert_batch(conn, data_batch)

        print()
        print("=" * 60)
        print(f"✓ Successfully generated {count:,} readings")
        print("=" * 60)
        print()

        # Show sample data
        print("Sample data:")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT time, sensor_id, temperature, humidity, pressure
            FROM sensor_data
            ORDER BY time DESC
            LIMIT 5
        """)

        print(f"{'Time':<20} {'Sensor':<15} {'Temp (°C)':<12} {'Humidity (%)':<15} {'Pressure (hPa)':<15}")
        print("-" * 80)

        for row in cursor.fetchall():
            print(f"{row[0].strftime('%Y-%m-%d %H:%M:%S'):<20} {row[1]:<15} {row[2]:<12.2f} {row[3]:<15.2f} {row[4]:<15.2f}")

        cursor.close()

        print()
        print("Next steps:")
        print("  1. Refresh aggregates: python3 refresh_aggregates.py")
        print("  2. Start API: python3 app/api.py")
        print("  3. Query data: curl http://localhost:5000/api/sensors")
        print()

    except Exception as e:
        print(f"\n✗ Error generating data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Generate IoT sensor data for TimescaleDB'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days of historical data (default: 30)'
    )

    parser.add_argument(
        '--sensors',
        type=int,
        default=10,
        help='Number of sensors (default: 10)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Seconds between readings per sensor (default: 60)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for inserts (default: 1000)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.days < 1:
        print("Error: --days must be at least 1")
        sys.exit(1)

    if args.sensors < 1:
        print("Error: --sensors must be at least 1")
        sys.exit(1)

    if args.interval < 1:
        print("Error: --interval must be at least 1")
        sys.exit(1)

    # Generate data
    generate_data(
        days=args.days,
        num_sensors=args.sensors,
        interval_seconds=args.interval,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
