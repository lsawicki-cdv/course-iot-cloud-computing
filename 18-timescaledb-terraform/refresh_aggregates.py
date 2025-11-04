#!/usr/bin/env python3
"""
Refresh Continuous Aggregates Script

This script manually refreshes all continuous aggregates.
Typically run by cron job to keep aggregates up-to-date.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
import sys


# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'iotdata',
    'user': 'postgres',
    'password': 'postgres'
}


def refresh_continuous_aggregate(conn, view_name, start_time=None, end_time=None):
    """
    Refresh a continuous aggregate.

    Args:
        conn: Database connection
        view_name: Name of the materialized view
        start_time: Start of refresh window (None = beginning of time)
        end_time: End of refresh window (None = now)
    """
    cursor = conn.cursor()

    try:
        print(f"Refreshing {view_name}...", end=" ")

        if start_time and end_time:
            cursor.execute(
                f"CALL refresh_continuous_aggregate(%s, %s, %s);",
                (view_name, start_time, end_time)
            )
        else:
            # Refresh all data
            cursor.execute(
                f"CALL refresh_continuous_aggregate(%s, NULL, NULL);",
                (view_name,)
            )

        conn.commit()
        print("✓")

    except Exception as e:
        print(f"✗ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()


def main():
    """Main function to refresh all continuous aggregates."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] Starting continuous aggregate refresh")

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)

        # Set connection to autocommit mode
        # This is required because CALL refresh_continuous_aggregate()
        # cannot run inside a transaction block
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Refresh all continuous aggregates
        # Note: Automated refresh policies handle this, but manual refresh
        # can be useful after bulk data inserts or for immediate updates

        refresh_continuous_aggregate(conn, 'sensor_data_hourly')
        refresh_continuous_aggregate(conn, 'sensor_data_daily')
        refresh_continuous_aggregate(conn, 'sensor_data_monthly')

        conn.close()

        print(f"[{timestamp}] Refresh completed successfully")

    except Exception as e:
        print(f"[{timestamp}] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
