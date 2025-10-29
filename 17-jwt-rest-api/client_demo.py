#!/usr/bin/env python3
"""
JWT REST API Client Demo

This script demonstrates how to interact with the JWT-protected REST API.
It shows the complete flow: registration, login, and accessing protected endpoints.
"""

import requests
import json
import time
from datetime import datetime


# API Configuration
BASE_URL = "http://localhost:5000/api"

# Test user credentials
TEST_USERNAME = "iot_user_demo"
TEST_PASSWORD = "secure_password_123"
TEST_EMAIL = "iot_demo@example.com"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_response(response):
    """Print HTTP response in a formatted way."""
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")


def health_check():
    """Check if API is running."""
    print_section("1. Health Check (Public Endpoint)")
    print(f"GET {BASE_URL}/health")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response(response)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to API server.")
        print("Make sure the server is running: python app.py")
        return False


def register_user():
    """Register a new user."""
    print_section("2. Register New User (Public Endpoint)")
    print(f"POST {BASE_URL}/register")

    payload = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
        "email": TEST_EMAIL
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(f"{BASE_URL}/register", json=payload)
    print_response(response)

    return response.status_code in [201, 409]  # 201 = created, 409 = already exists


def login():
    """Login and receive JWT token."""
    print_section("3. Login and Receive JWT Token (Public Endpoint)")
    print(f"POST {BASE_URL}/login")

    payload = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(f"{BASE_URL}/login", json=payload)
    print_response(response)

    if response.status_code == 200:
        data = response.json()
        token = data.get('token')
        print(f"\n✓ JWT Token received!")
        print(f"  Token (first 50 chars): {token[:50]}...")
        print(f"  Expires in: {data.get('expires_in')} seconds")
        return token
    else:
        print("❌ Login failed")
        return None


def get_profile(token):
    """Get user profile using JWT token."""
    print_section("4. Get User Profile (Protected Endpoint)")
    print(f"GET {BASE_URL}/profile")
    print(f"Authorization: Bearer {token[:50]}...")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BASE_URL}/profile", headers=headers)
    print_response(response)

    return response.status_code == 200


def create_sensor(token, sensor_name, sensor_type, location):
    """Create a new sensor."""
    print_section(f"5. Create Sensor: {sensor_name} (Protected Endpoint)")
    print(f"POST {BASE_URL}/sensors")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "name": sensor_name,
        "type": sensor_type,
        "location": location
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(f"{BASE_URL}/sensors", json=payload, headers=headers)
    print_response(response)

    if response.status_code == 201:
        data = response.json()
        sensor_id = data['sensor']['sensor_id']
        print(f"\n✓ Sensor created with ID: {sensor_id}")
        return sensor_id
    return None


def add_sensor_data(token, sensor_id, value, unit):
    """Add telemetry data to sensor."""
    print_section(f"6. Add Telemetry Data to {sensor_id}")
    print(f"POST {BASE_URL}/sensors/{sensor_id}/data")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "value": value,
        "unit": unit
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(f"{BASE_URL}/sensors/{sensor_id}/data", json=payload, headers=headers)
    print_response(response)

    return response.status_code == 201


def get_sensor_data(token, sensor_id):
    """Get telemetry data from sensor."""
    print_section(f"7. Get Telemetry Data from {sensor_id}")
    print(f"GET {BASE_URL}/sensors/{sensor_id}/data")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BASE_URL}/sensors/{sensor_id}/data", headers=headers)
    print_response(response)

    return response.status_code == 200


def list_sensors(token):
    """List all user's sensors."""
    print_section("8. List All Sensors (Protected Endpoint)")
    print(f"GET {BASE_URL}/sensors")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(f"{BASE_URL}/sensors", headers=headers)
    print_response(response)

    return response.status_code == 200


def test_without_token():
    """Attempt to access protected endpoint without token."""
    print_section("9. Test Access Without Token (Should Fail)")
    print(f"GET {BASE_URL}/profile")
    print("Authorization header: (not provided)")

    response = requests.get(f"{BASE_URL}/profile")
    print_response(response)

    if response.status_code == 401:
        print("\n✓ Correctly denied access without token")
    return response.status_code == 401


def test_invalid_token():
    """Attempt to access protected endpoint with invalid token."""
    print_section("10. Test Access With Invalid Token (Should Fail)")
    print(f"GET {BASE_URL}/profile")

    headers = {
        "Authorization": "Bearer invalid.token.here"
    }

    response = requests.get(f"{BASE_URL}/profile", headers=headers)
    print_response(response)

    if response.status_code == 401:
        print("\n✓ Correctly denied access with invalid token")
    return response.status_code == 401


def main():
    """Run the complete demo."""
    print("=" * 70)
    print(" JWT REST API Client Demo")
    print("=" * 70)
    print(f" Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Health check
    if not health_check():
        return

    time.sleep(1)

    # 2. Register user
    if not register_user():
        print("\n❌ Registration failed")
        return

    time.sleep(1)

    # 3. Login and get token
    token = login()
    if not token:
        print("\n❌ Could not obtain JWT token")
        return

    time.sleep(1)

    # 4. Get profile
    get_profile(token)
    time.sleep(1)

    # 5. Create sensors
    sensor1_id = create_sensor(token, "Temperature Sensor A", "temperature", "Server Room")
    time.sleep(1)

    sensor2_id = create_sensor(token, "Humidity Sensor B", "humidity", "Warehouse")
    time.sleep(1)

    # 6. Add data to sensors
    if sensor1_id:
        add_sensor_data(token, sensor1_id, 23.5, "celsius")
        time.sleep(1)
        add_sensor_data(token, sensor1_id, 24.1, "celsius")
        time.sleep(1)

    if sensor2_id:
        add_sensor_data(token, sensor2_id, 65.2, "percent")
        time.sleep(1)

    # 7. Get sensor data
    if sensor1_id:
        get_sensor_data(token, sensor1_id)
        time.sleep(1)

    # 8. List all sensors
    list_sensors(token)
    time.sleep(1)

    # 9. Test security - no token
    test_without_token()
    time.sleep(1)

    # 10. Test security - invalid token
    test_invalid_token()

    # Summary
    print_section("Demo Complete!")
    print("✓ Successfully demonstrated:")
    print("  - User registration")
    print("  - JWT token authentication")
    print("  - Protected endpoint access")
    print("  - Sensor creation and data management")
    print("  - Security validation (token required)")
    print()
    print("Next steps:")
    print("  - Try modifying the client to add more sensors")
    print("  - Test token expiration by waiting for token to expire")
    print("  - Explore the API with curl or Postman")
    print("  - Read the token payload with decode_jwt.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
