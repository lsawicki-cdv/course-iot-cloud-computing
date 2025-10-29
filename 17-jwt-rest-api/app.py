#!/usr/bin/env python3
"""
Flask REST API with JWT Authentication

This API demonstrates JWT token-based authentication for securing REST endpoints.
Perfect for IoT applications that need secure device-to-cloud communication.
"""

from flask import Flask, request, jsonify
from functools import wraps
import jwt
import datetime
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_EXPIRATION_MINUTES = int(os.getenv('JWT_EXPIRATION_MINUTES', 30))

# In-memory storage (in production, use a real database)
users_db = {}  # {username: {password_hash, email, user_id}}
sensors_db = {}  # {sensor_id: {name, type, location, owner_id}}
telemetry_db = {}  # {sensor_id: [data_points]}

# Helper function to hash passwords
def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


# JWT Token Generation
def generate_token(user_id, username):
    """
    Generate a JWT token for authenticated user.

    Args:
        user_id: Unique user identifier
        username: Username

    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRATION_MINUTES),
        'iat': datetime.datetime.utcnow()
    }

    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token


# JWT Token Validation Decorator
def token_required(f):
    """
    Decorator to protect endpoints with JWT authentication.

    Usage:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'message': f'Hello {current_user["username"]}'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check if Authorization header exists
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']

            # Format: "Bearer <token>"
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format. Use: Bearer <token>'}), 401

        if not token:
            return jsonify({'error': 'Missing Authorization header'}), 401

        try:
            # Decode and verify token
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = {
                'user_id': payload['user_id'],
                'username': payload['username']
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        # Pass current_user to the route function
        return f(current_user, *args, **kwargs)

    return decorated


# =============================================================================
# PUBLIC ENDPOINTS (No authentication required)
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'JWT REST API',
        'timestamp': datetime.datetime.utcnow().isoformat()
    })


@app.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
        {
            "username": "string",
            "password": "string",
            "email": "string"
        }
    """
    data = request.get_json()

    # Validate input
    if not data or not all(k in data for k in ['username', 'password', 'email']):
        return jsonify({'error': 'Missing required fields: username, password, email'}), 400

    username = data['username']
    password = data['password']
    email = data['email']

    # Check if user already exists
    if username in users_db:
        return jsonify({'error': 'User already exists'}), 409

    # Basic validation
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Create user
    user_id = len(users_db) + 1
    users_db[username] = {
        'user_id': user_id,
        'password_hash': hash_password(password),
        'email': email,
        'created_at': datetime.datetime.utcnow().isoformat()
    }

    return jsonify({
        'message': 'User registered successfully',
        'user_id': user_id,
        'username': username
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    """
    Login and receive JWT token.

    Request body:
        {
            "username": "string",
            "password": "string"
        }

    Returns:
        {
            "token": "jwt_token_string",
            "expires_in": seconds,
            "username": "string"
        }
    """
    data = request.get_json()

    # Validate input
    if not data or not all(k in data for k in ['username', 'password']):
        return jsonify({'error': 'Missing username or password'}), 400

    username = data['username']
    password = data['password']

    # Check if user exists
    if username not in users_db:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Verify password
    user = users_db[username]
    if user['password_hash'] != hash_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Generate token
    token = generate_token(user['user_id'], username)

    return jsonify({
        'token': token,
        'expires_in': JWT_EXPIRATION_MINUTES * 60,  # seconds
        'username': username,
        'message': 'Login successful'
    })


# =============================================================================
# PROTECTED ENDPOINTS (JWT authentication required)
# =============================================================================

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get current user's profile (requires JWT token)."""
    username = current_user['username']
    user_data = users_db.get(username, {})

    return jsonify({
        'user_id': current_user['user_id'],
        'username': username,
        'email': user_data.get('email'),
        'created_at': user_data.get('created_at')
    })


@app.route('/api/sensors', methods=['GET'])
@token_required
def get_sensors(current_user):
    """Get all sensors owned by current user."""
    user_id = current_user['user_id']

    # Filter sensors by owner
    user_sensors = {
        sensor_id: sensor_data
        for sensor_id, sensor_data in sensors_db.items()
        if sensor_data['owner_id'] == user_id
    }

    return jsonify({
        'sensors': user_sensors,
        'count': len(user_sensors)
    })


@app.route('/api/sensors', methods=['POST'])
@token_required
def create_sensor(current_user):
    """
    Create a new IoT sensor.

    Request body:
        {
            "name": "string",
            "type": "string (e.g., temperature, humidity)",
            "location": "string"
        }
    """
    data = request.get_json()

    # Validate input
    if not data or not all(k in data for k in ['name', 'type', 'location']):
        return jsonify({'error': 'Missing required fields: name, type, location'}), 400

    # Create sensor
    sensor_id = f"sensor_{len(sensors_db) + 1}"
    sensors_db[sensor_id] = {
        'sensor_id': sensor_id,
        'name': data['name'],
        'type': data['type'],
        'location': data['location'],
        'owner_id': current_user['user_id'],
        'created_at': datetime.datetime.utcnow().isoformat()
    }

    # Initialize telemetry storage for this sensor
    telemetry_db[sensor_id] = []

    return jsonify({
        'message': 'Sensor created successfully',
        'sensor': sensors_db[sensor_id]
    }), 201


@app.route('/api/sensors/<sensor_id>/data', methods=['GET'])
@token_required
def get_sensor_data(current_user, sensor_id):
    """Get telemetry data for a specific sensor."""
    # Check if sensor exists
    if sensor_id not in sensors_db:
        return jsonify({'error': 'Sensor not found'}), 404

    # Check ownership
    sensor = sensors_db[sensor_id]
    if sensor['owner_id'] != current_user['user_id']:
        return jsonify({'error': 'Access denied'}), 403

    # Get telemetry data
    data = telemetry_db.get(sensor_id, [])

    return jsonify({
        'sensor_id': sensor_id,
        'sensor_name': sensor['name'],
        'data_points': data,
        'count': len(data)
    })


@app.route('/api/sensors/<sensor_id>/data', methods=['POST'])
@token_required
def add_sensor_data(current_user, sensor_id):
    """
    Add telemetry data for a sensor.

    Request body:
        {
            "value": number,
            "unit": "string (e.g., celsius, percent)"
        }
    """
    # Check if sensor exists
    if sensor_id not in sensors_db:
        return jsonify({'error': 'Sensor not found'}), 404

    # Check ownership
    sensor = sensors_db[sensor_id]
    if sensor['owner_id'] != current_user['user_id']:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()

    # Validate input
    if not data or 'value' not in data:
        return jsonify({'error': 'Missing required field: value'}), 400

    # Add telemetry data point
    data_point = {
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'value': data['value'],
        'unit': data.get('unit', 'unknown')
    }

    telemetry_db[sensor_id].append(data_point)

    return jsonify({
        'message': 'Data added successfully',
        'sensor_id': sensor_id,
        'data_point': data_point
    }), 201


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("=" * 70)
    print("JWT REST API Server")
    print("=" * 70)
    print(f"Token expiration: {JWT_EXPIRATION_MINUTES} minutes")
    print(f"Secret key configured: {'Yes' if app.config['SECRET_KEY'] != 'dev-secret-key-change-in-production' else 'No (using default)'}")
    print()
    print("Available endpoints:")
    print("  Public:")
    print("    POST /api/register  - Register new user")
    print("    POST /api/login     - Login and get JWT token")
    print("    GET  /api/health    - Health check")
    print()
    print("  Protected (requires JWT token):")
    print("    GET  /api/profile              - Get user profile")
    print("    GET  /api/sensors              - List user's sensors")
    print("    POST /api/sensors              - Create new sensor")
    print("    GET  /api/sensors/<id>/data    - Get sensor data")
    print("    POST /api/sensors/<id>/data    - Add sensor data")
    print()
    print("Starting server on http://127.0.0.1:5000")
    print("=" * 70)
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)
