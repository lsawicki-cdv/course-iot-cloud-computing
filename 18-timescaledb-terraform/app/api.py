#!/usr/bin/env python3
"""
TimescaleDB REST API

Provides efficient endpoints for querying time-series IoT data.
Demonstrates the power of continuous aggregates for fast queries.
"""

from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta
import time


app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'iotdata'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}


def get_db_connection():
    """Get database connection with RealDictCursor."""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def parse_period(period_str):
    """
    Parse period string (e.g., '1d', '1w', '1m', '1y') to timedelta.

    Args:
        period_str: Period string

    Returns:
        timedelta object
    """
    if not period_str:
        return timedelta(days=1)  # Default: 1 day

    period_map = {
        'h': 'hours',
        'd': 'days',
        'w': 'weeks'
    }

    try:
        value = int(period_str[:-1])
        unit = period_str[-1].lower()

        if unit == 'm':  # months
            return timedelta(days=value * 30)
        elif unit == 'y':  # years
            return timedelta(days=value * 365)
        elif unit in period_map:
            kwargs = {period_map[unit]: value}
            return timedelta(**kwargs)
        else:
            return timedelta(days=1)
    except:
        return timedelta(days=1)


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({
            'status': 'healthy',
            'service': 'TimescaleDB API',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/api/sensors', methods=['GET'])
def list_sensors():
    """List all sensors with their latest reading time."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                sensor_id,
                MAX(time) as last_reading,
                COUNT(*) as total_readings
            FROM sensor_data
            GROUP BY sensor_id
            ORDER BY sensor_id
        """)

        sensors = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify({
            'sensors': sensors,
            'count': len(sensors)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<sensor_id>/current', methods=['GET'])
def get_current_reading(sensor_id):
    """Get the most recent reading for a sensor."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT time, sensor_id, temperature, humidity, pressure
            FROM sensor_data
            WHERE sensor_id = %s
            ORDER BY time DESC
            LIMIT 1
        """, (sensor_id,))

        reading = cursor.fetchone()
        cursor.close()
        conn.close()

        if not reading:
            return jsonify({'error': 'Sensor not found'}), 404

        return jsonify(reading)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<sensor_id>/raw', methods=['GET'])
def get_raw_data(sensor_id):
    """
    Get raw sensor data for a specified period.

    Query params:
        period: Time period (e.g., '1h', '1d', '1w')
    """
    period_str = request.args.get('period', '1d')
    period = parse_period(period_str)

    start_time = datetime.now() - period

    try:
        start_query = time.time()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT time, temperature, humidity, pressure
            FROM sensor_data
            WHERE sensor_id = %s
            AND time > %s
            ORDER BY time ASC
        """, (sensor_id, start_time))

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        query_time = time.time() - start_query

        return jsonify({
            'sensor_id': sensor_id,
            'period': period_str,
            'data_points': len(data),
            'query_time_ms': round(query_time * 1000, 2),
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<sensor_id>/hourly', methods=['GET'])
def get_hourly_aggregates(sensor_id):
    """
    Get hourly aggregated data using continuous aggregates.

    Query params:
        period: Time period (e.g., '1d', '1w', '1m')
    """
    period_str = request.args.get('period', '1w')
    period = parse_period(period_str)

    start_time = datetime.now() - period

    try:
        start_query = time.time()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                bucket as time,
                avg_temperature,
                min_temperature,
                max_temperature,
                avg_humidity,
                avg_pressure,
                reading_count
            FROM sensor_data_hourly
            WHERE sensor_id = %s
            AND bucket > %s
            ORDER BY bucket ASC
        """, (sensor_id, start_time))

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        query_time = time.time() - start_query

        return jsonify({
            'sensor_id': sensor_id,
            'period': period_str,
            'aggregation': 'hourly',
            'data_points': len(data),
            'query_time_ms': round(query_time * 1000, 2),
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<sensor_id>/daily', methods=['GET'])
def get_daily_aggregates(sensor_id):
    """
    Get daily aggregated data using continuous aggregates.

    Query params:
        period: Time period (e.g., '1w', '1m', '1y')
    """
    period_str = request.args.get('period', '1m')
    period = parse_period(period_str)

    start_time = datetime.now() - period

    try:
        start_query = time.time()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                bucket as time,
                avg_temperature,
                min_temperature,
                max_temperature,
                avg_humidity,
                avg_pressure,
                reading_count
            FROM sensor_data_daily
            WHERE sensor_id = %s
            AND bucket > %s
            ORDER BY bucket ASC
        """, (sensor_id, start_time))

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        query_time = time.time() - start_query

        return jsonify({
            'sensor_id': sensor_id,
            'period': period_str,
            'aggregation': 'daily',
            'data_points': len(data),
            'query_time_ms': round(query_time * 1000, 2),
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensors/<sensor_id>/monthly', methods=['GET'])
def get_monthly_aggregates(sensor_id):
    """
    Get monthly aggregated data using continuous aggregates.

    Query params:
        period: Time period (e.g., '1y', '2y')
    """
    period_str = request.args.get('period', '1y')
    period = parse_period(period_str)

    start_time = datetime.now() - period

    try:
        start_query = time.time()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                bucket as time,
                avg_temperature,
                min_temperature,
                max_temperature,
                avg_humidity,
                avg_pressure,
                reading_count
            FROM sensor_data_monthly
            WHERE sensor_id = %s
            AND bucket > %s
            ORDER BY bucket ASC
        """, (sensor_id, start_time))

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        query_time = time.time() - start_query

        return jsonify({
            'sensor_id': sensor_id,
            'period': period_str,
            'aggregation': 'monthly',
            'data_points': len(data),
            'query_time_ms': round(query_time * 1000, 2),
            'data': data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/performance', methods=['GET'])
def performance_comparison():
    """
    Compare performance between raw queries and continuous aggregates.

    Demonstrates the power of continuous aggregates.
    """
    sensor_id = request.args.get('sensor_id', 'sensor_001')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        results = {}

        # Test 1: Raw query for hourly averages (last week)
        start = time.time()
        cursor.execute("""
            SELECT
                time_bucket('1 hour', time) AS hour,
                AVG(temperature) as avg_temp
            FROM sensor_data
            WHERE sensor_id = %s
            AND time > NOW() - INTERVAL '7 days'
            GROUP BY hour
            ORDER BY hour
        """, (sensor_id,))
        raw_data = cursor.fetchall()
        raw_time = time.time() - start

        # Test 2: Continuous aggregate query
        start = time.time()
        cursor.execute("""
            SELECT bucket, avg_temperature
            FROM sensor_data_hourly
            WHERE sensor_id = %s
            AND bucket > NOW() - INTERVAL '7 days'
            ORDER BY bucket
        """, (sensor_id,))
        agg_data = cursor.fetchall()
        agg_time = time.time() - start

        cursor.close()
        conn.close()

        speedup = raw_time / agg_time if agg_time > 0 else 0

        return jsonify({
            'sensor_id': sensor_id,
            'period': '7 days',
            'raw_query': {
                'time_ms': round(raw_time * 1000, 2),
                'data_points': len(raw_data)
            },
            'aggregate_query': {
                'time_ms': round(agg_time * 1000, 2),
                'data_points': len(agg_data)
            },
            'speedup': f"{speedup:.1f}x",
            'improvement_percent': round((1 - agg_time / raw_time) * 100, 1)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("TimescaleDB REST API")
    print("=" * 60)
    print(f"Database: {DB_CONFIG['database']} @ {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print()
    print("Endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/sensors")
    print("  GET  /api/sensors/<id>/current")
    print("  GET  /api/sensors/<id>/raw?period=1d")
    print("  GET  /api/sensors/<id>/hourly?period=1w")
    print("  GET  /api/sensors/<id>/daily?period=1m")
    print("  GET  /api/sensors/<id>/monthly?period=1y")
    print("  GET  /api/stats/performance?sensor_id=sensor_001")
    print()
    print("Starting server on http://0.0.0.0:5000")
    print("=" * 60)
    print()

    app.run(host='0.0.0.0', port=5000, debug=False)
