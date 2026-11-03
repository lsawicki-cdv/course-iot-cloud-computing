import random

import psycopg

# Connection details are read from the environment variables:
# PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD and PGSSLMODE
device_ids = ["device-01", "device-02", "device-03"]
readings_per_device = 20


def create_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id SERIAL PRIMARY KEY,
            device_id TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            pressure REAL NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    print("Table 'sensor_readings' is ready")


def insert_readings(conn):
    with conn.cursor() as cursor:
        for device_id in device_ids:
            for minutes_ago in range(readings_per_device):
                # Generate random sensor data, one reading per minute
                cursor.execute(
                    """
                    INSERT INTO sensor_readings (device_id, temperature, humidity, pressure, recorded_at)
                    VALUES (%s, %s, %s, %s, now() - make_interval(mins => %s))
                    """,
                    (device_id, random.uniform(20, 30), random.uniform(40, 60),
                     random.uniform(900, 1100), minutes_ago))
    print(f"Inserted {len(device_ids) * readings_per_device} readings")


def show_statistics(conn):
    count = conn.execute("SELECT count(*) FROM sensor_readings").fetchone()[0]
    print(f"\nAll readings in the table: {count}")

    print("\nAverage values per device:")
    rows = conn.execute("""
        SELECT device_id, count(*), avg(temperature), avg(humidity), avg(pressure)
        FROM sensor_readings
        GROUP BY device_id
        ORDER BY device_id
    """).fetchall()
    for device_id, readings, temperature, humidity, pressure in rows:
        print(f"{device_id}: {readings} readings, temperature {temperature:.1f} C, "
              f"humidity {humidity:.1f} %, pressure {pressure:.1f} hPa")

    print("\nLatest 5 readings:")
    rows = conn.execute("""
        SELECT device_id, temperature, recorded_at
        FROM sensor_readings
        ORDER BY recorded_at DESC
        LIMIT 5
    """).fetchall()
    for device_id, temperature, recorded_at in rows:
        print(f"{recorded_at:%Y-%m-%d %H:%M:%S} {device_id}: {temperature:.1f} C")


def main():
    with psycopg.connect() as conn:
        print(f"Connected to {conn.info.host}, database '{conn.info.dbname}'")
        create_table(conn)
        insert_readings(conn)
        conn.commit()
        show_statistics(conn)


if __name__ == "__main__":
    main()
