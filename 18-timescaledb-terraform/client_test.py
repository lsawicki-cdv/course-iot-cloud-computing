#!/usr/bin/env python3
"""
TimescaleDB API Client Test Script

Demonstrates querying the API for different time periods
and comparing performance between raw and aggregated queries.
"""

import requests
import argparse
import json


def test_api(host, port):
    """Test the TimescaleDB API endpoints."""
    base_url = f"http://{host}:{port}/api"

    print("=" * 70)
    print("TimescaleDB API Client Test")
    print("=" * 70)
    print(f"API URL: {base_url}")
    print()

    # Test 1: Health check
    print("1. Health Check")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the API server is running!")
        return
    print()

    # Test 2: List sensors
    print("2. List All Sensors")
    print("-" * 70)
    response = requests.get(f"{base_url}/sensors")
    data = response.json()
    print(f"Found {data['count']} sensors")
    for sensor in data['sensors'][:5]:  # Show first 5
        print(f"  {sensor['sensor_id']}: {sensor['total_readings']} readings")
    print()

    # Get first sensor for testing
    if data['count'] == 0:
        print("No sensors found. Run generate_data.py first!")
        return

    sensor_id = data['sensors'][0]['sensor_id']
    print(f"Using {sensor_id} for tests")
    print()

    # Test 3: Current reading
    print("3. Current Reading")
    print("-" * 70)
    response = requests.get(f"{base_url}/sensors/{sensor_id}/current")
    print(json.dumps(response.json(), indent=2))
    print()

    # Test 4: Hourly aggregates (last week)
    print("4. Hourly Aggregates (Last Week)")
    print("-" * 70)
    response = requests.get(f"{base_url}/sensors/{sensor_id}/hourly?period=1w")
    data = response.json()
    print(f"Data points: {data['data_points']}")
    print(f"Query time: {data['query_time_ms']} ms")
    if data['data']:
        print("\nSample data (first 3 points):")
        for point in data['data'][:3]:
            print(f"  {point['time']}: {point['avg_temperature']:.2f}°C")
    print()

    # Test 5: Daily aggregates (last month)
    print("5. Daily Aggregates (Last Month)")
    print("-" * 70)
    response = requests.get(f"{base_url}/sensors/{sensor_id}/daily?period=1m")
    data = response.json()
    print(f"Data points: {data['data_points']}")
    print(f"Query time: {data['query_time_ms']} ms")
    print()

    # Test 6: Monthly aggregates (last year)
    print("6. Monthly Aggregates (Last Year)")
    print("-" * 70)
    response = requests.get(f"{base_url}/sensors/{sensor_id}/monthly?period=1y")
    data = response.json()
    print(f"Data points: {data['data_points']}")
    print(f"Query time: {data['query_time_ms']} ms")
    print()

    # Test 7: Performance comparison
    print("7. Performance Comparison (Raw vs Aggregates)")
    print("-" * 70)
    response = requests.get(f"{base_url}/stats/performance?sensor_id={sensor_id}")
    data = response.json()
    print(f"Period: {data['period']}")
    print(f"\nRaw Query:")
    print(f"  Time: {data['raw_query']['time_ms']} ms")
    print(f"  Data points: {data['raw_query']['data_points']}")
    print(f"\nAggregate Query:")
    print(f"  Time: {data['aggregate_query']['time_ms']} ms")
    print(f"  Data points: {data['aggregate_query']['data_points']}")
    print(f"\n✓ Speedup: {data['speedup']}")
    print(f"✓ Improvement: {data['improvement_percent']}%")
    print()

    print("=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Test TimescaleDB API endpoints'
    )

    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='API host (default: localhost)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='API port (default: 5000)'
    )

    args = parser.parse_args()

    test_api(args.host, args.port)


if __name__ == "__main__":
    main()
