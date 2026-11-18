#!/usr/bin/env python3
"""
IoT Device Simulator with X.509 Certificate Authentication (AWS IoT Core)

This simulator demonstrates how to connect to AWS IoT Core using
an X.509 certificate that you generated yourself.

Key differences from symmetric key authentication:
- No connection string or password needed
- Private key never leaves the device
- More secure for production environments
- Can use Hardware Security Modules (HSM)
"""

import json
import os
import random
import ssl
import sys
import threading
import time
from datetime import datetime, timezone
from paho.mqtt import client as mqtt


# =============================================================================
# CONFIGURATION - Update these values for your AWS IoT Core
# =============================================================================

# e.g., "a1b2c3d4e5f6g7-ats.iot.eu-west-2.amazonaws.com"
IOT_ENDPOINT = "your-endpoint-ats.iot.eu-west-2.amazonaws.com"
THING_NAME = "device-x509-test"  # Must match the thing name and the client ID in the policy

CERTIFICATE_FILE = "device-cert.pem"  # Public certificate
PRIVATE_KEY_FILE = "device-key.pem"   # Private key (keep secret!)
ROOT_CA_FILE = "AmazonRootCA1.pem"    # Amazon Root CA 1, verifies the IoT Core server
IOT_PORT = 8883

# =============================================================================

CONNECT_TIMEOUT_SECONDS = 15
PUBLISH_TIMEOUT_SECONDS = 10

# Set by the CONNACK callback; connect_result holds the MQTT return code
connected_event = threading.Event()
connect_result = None


def check_configuration():
    """
    Verify that configuration is set and certificate files exist.
    """
    errors = []

    if IOT_ENDPOINT == "your-endpoint-ats.iot.eu-west-2.amazonaws.com":
        errors.append(
            "⚠ Please update IOT_ENDPOINT with your actual IoT Core endpoint")

    if THING_NAME == "device-x509-test":
        print("⚠ Using default THING_NAME. Update if you used a different thing name.")

    if not os.path.exists(CERTIFICATE_FILE):
        errors.append(f"⚠ Certificate file '{CERTIFICATE_FILE}' not found!")
        errors.append("   Run 'python ../generate_certificate.py' first")

    if not os.path.exists(PRIVATE_KEY_FILE):
        errors.append(f"⚠ Private key file '{PRIVATE_KEY_FILE}' not found!")
        errors.append("   Run 'python ../generate_certificate.py' first")

    if not os.path.exists(ROOT_CA_FILE):
        errors.append(f"⚠ Root CA file '{ROOT_CA_FILE}' not found!")
        errors.append("   It ships with the exercise: restore it from the repository")

    if errors:
        print("Configuration Errors:")
        print("-" * 60)
        for error in errors:
            print(error)
        print("-" * 60)
        print("\nPlease fix the errors above and try again.")
        sys.exit(1)


def on_connect(client, userdata, flags, rc):
    """
    Called when the CONNACK arrives; rc 0 means IoT Core accepted the connection.
    """
    global connect_result
    connect_result = rc
    connected_event.set()


def create_x509_client():
    """
    Create an MQTT client that authenticates with the X.509 certificate.

    Returns:
        mqtt.Client: The configured client (not connected yet)
    """
    print("Creating X.509 authenticated client...")
    print(f"  Endpoint: {IOT_ENDPOINT}")
    print(f"  Thing name: {THING_NAME}")
    print(f"  Certificate: {CERTIFICATE_FILE}")
    print(f"  Private Key: {PRIVATE_KEY_FILE}")
    print(f"  Root CA: {ROOT_CA_FILE}")
    print()

    # The client ID must match the one allowed in the device policy
    client = mqtt.Client(client_id=THING_NAME)
    client.on_connect = on_connect

    # No username or password: the certificate is the identity.
    # CERT_REQUIRED makes the device verify the IoT Core server certificate.
    client.tls_set(ca_certs=ROOT_CA_FILE, certfile=CERTIFICATE_FILE, keyfile=PRIVATE_KEY_FILE,
                   cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)

    print("✓ Client created successfully")
    print()
    print("Understanding X.509 Authentication:")
    print("-" * 60)
    print("• Your device uses TLS client certificate authentication")
    print("• Private key signs the TLS handshake (proves you own the certificate)")
    print("• IoT Core checks that the certificate is registered and active")
    print("• No secrets transmitted over the network!")
    print("-" * 60)
    print()

    return client


def generate_telemetry():
    """
    Generate sample telemetry data (temperature and humidity).

    Returns:
        dict: Telemetry data
    """
    temperature = round(20 + random.uniform(-5, 15), 2)
    humidity = round(40 + random.uniform(-10, 20), 2)

    return {
        "deviceId": THING_NAME,
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def send_telemetry(client, message_count=10, interval_seconds=5):
    """
    Send telemetry messages to IoT Core.

    Args:
        client: The connected MQTT client
        message_count: Number of messages to send
        interval_seconds: Delay between messages
    """
    topic = f"devices/{THING_NAME}/messages/events/"
    print(f"MQTT topic: {topic}")
    print(
        f"Sending {message_count} messages (one every {interval_seconds} seconds)...")
    print()

    for i in range(message_count):
        message_json = json.dumps(generate_telemetry())

        # Send to IoT Core with QoS 1: wait for the PUBACK from the broker
        print(f"[{i+1}/{message_count}] Sending: {message_json}")
        info = client.publish(topic, message_json, qos=1)
        info.wait_for_publish(timeout=PUBLISH_TIMEOUT_SECONDS)

        if info.is_published():
            print("  ✓ Message acknowledged by IoT Core via secure TLS connection")
        else:
            print("  ✗ Message not acknowledged (check the device policy allows this topic)")

        if i < message_count - 1:
            time.sleep(interval_seconds)

    print()
    print(f"✓ Completed sending {message_count} messages")


def print_troubleshooting():
    """Print common causes of connection failures."""
    print()
    print("Troubleshooting:")
    print("  • Verify IOT_ENDPOINT is correct (aws iot describe-endpoint --endpoint-type iot:Data-ATS)")
    print("  • Ensure the certificate is registered and ACTIVE in IoT Core, in this region")
    print("  • Check the policy is attached to the certificate and allows connect for your client ID")
    print("  • Check the certificate is attached to the thing and THING_NAME matches")
    print("  • Use the same device-cert.pem and device-key.pem pair you registered")


def main():
    """
    Main function to run the device simulator.
    """
    print("=" * 70)
    print("IoT Device Simulator - X.509 Certificate Authentication (AWS)")
    print("=" * 70)
    print()

    check_configuration()

    client = create_x509_client()

    try:
        # Connect to IoT Core; the hostname is also sent as SNI
        print("Connecting to AWS IoT Core...")
        client.connect(IOT_ENDPOINT, IOT_PORT)
        # Network loop in the background: handles the TLS connection, acknowledgements and callbacks
        client.loop_start()

        if not connected_event.wait(CONNECT_TIMEOUT_SECONDS):
            raise TimeoutError("no CONNACK from IoT Core")
        if connect_result != 0:
            raise ConnectionError(f"IoT Core refused the connection (MQTT return code {connect_result})")

        print("✓ Connected successfully!")
        print()
        print("TLS Connection Established:")
        print("  • Server verified: IoT Core certificate checked with Amazon Root CA 1")
        print("  • Client verified: Your device certificate authenticated")
        print("  • Encrypted channel: All data is now encrypted with TLS")
        print()

        send_telemetry(
            client,
            message_count=10,
            interval_seconds=5
        )

    except KeyboardInterrupt:
        print()
        print("Interrupted by user")

    except (OSError, ssl.SSLError, TimeoutError, ConnectionError) as e:
        print(f"Error: {e}")
        print_troubleshooting()

    finally:
        print()
        print("Disconnecting...")
        client.disconnect()
        client.loop_stop()
        print("✓ Disconnected")
        print()
        print("=" * 70)
        print("Simulator completed")
        print("=" * 70)


if __name__ == "__main__":
    main()
