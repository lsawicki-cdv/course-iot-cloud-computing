#!/usr/bin/env python3
"""
IoT Device Simulator with X.509 Certificate Authentication

This simulator demonstrates how to connect to Azure IoT Hub using
X.509 certificate authentication instead of connection strings.

Key differences from symmetric key authentication:
- No connection string needed
- Private key never leaves the device
- More secure for production environments
- Can use Hardware Security Modules (HSM)
"""

import asyncio
import random
import sys
import os
from datetime import datetime
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import X509
import json


# =============================================================================
# CONFIGURATION - Update these values for your IoT Hub
# =============================================================================

IOTHUB_HOSTNAME = "your-hub-name.azure-devices.net"  # e.g., "my-iot-hub.azure-devices.net"
DEVICE_ID = "device-x509-test"  # Must match the device ID in IoT Hub

CERTIFICATE_FILE = "device-cert.pem"  # Public certificate
PRIVATE_KEY_FILE = "device-key.pem"   # Private key (keep secret!)

# =============================================================================


def check_configuration():
    """
    Verify that configuration is set and certificate files exist.
    """
    errors = []

    if IOTHUB_HOSTNAME == "your-hub-name.azure-devices.net":
        errors.append("⚠ Please update IOTHUB_HOSTNAME with your actual IoT Hub hostname")

    if DEVICE_ID == "device-x509-test":
        print("⚠ Using default DEVICE_ID. Update if you used a different device ID.")

    if not os.path.exists(CERTIFICATE_FILE):
        errors.append(f"⚠ Certificate file '{CERTIFICATE_FILE}' not found!")
        errors.append("   Run 'python generate_certificate.py' first")

    if not os.path.exists(PRIVATE_KEY_FILE):
        errors.append(f"⚠ Private key file '{PRIVATE_KEY_FILE}' not found!")
        errors.append("   Run 'python generate_certificate.py' first")

    if errors:
        print("Configuration Errors:")
        print("-" * 60)
        for error in errors:
            print(error)
        print("-" * 60)
        print("\nPlease fix the errors above and try again.")
        sys.exit(1)


def create_x509_client():
    """
    Create an IoT Hub device client using X.509 certificate authentication.

    Returns:
        IoTHubDeviceClient: The authenticated client
    """
    print("Creating X.509 authenticated client...")
    print(f"  Hub: {IOTHUB_HOSTNAME}")
    print(f"  Device ID: {DEVICE_ID}")
    print(f"  Certificate: {CERTIFICATE_FILE}")
    print(f"  Private Key: {PRIVATE_KEY_FILE}")
    print()

    # Create X.509 object with certificate and key
    x509 = X509(
        cert_file=CERTIFICATE_FILE,
        key_file=PRIVATE_KEY_FILE,
        pass_phrase=None  # No password protection in this example
    )

    # Create the client
    # Note: No connection string needed! Authentication is via certificate
    client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=IOTHUB_HOSTNAME,
        device_id=DEVICE_ID,
        x509=x509
    )

    print("✓ Client created successfully")
    print()
    print("Understanding X.509 Authentication:")
    print("-" * 60)
    print("• Your device uses TLS client certificate authentication")
    print("• Private key signs the TLS handshake (proves you own the certificate)")
    print("• IoT Hub verifies the certificate thumbprint matches the device")
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
        "temperature": temperature,
        "humidity": humidity,
        "timestamp": datetime.utcnow().isoformat()
    }


async def send_telemetry(client, message_count=10, interval_seconds=5):
    """
    Send telemetry messages to IoT Hub.

    Args:
        client: The IoT Hub device client
        message_count: Number of messages to send
        interval_seconds: Delay between messages
    """
    print(f"Sending {message_count} messages (one every {interval_seconds} seconds)...")
    print()

    for i in range(message_count):
        try:
            # Generate telemetry
            telemetry = generate_telemetry()

            # Convert to JSON
            message_json = json.dumps(telemetry)

            # Send to IoT Hub
            print(f"[{i+1}/{message_count}] Sending: {message_json}")
            await client.send_message(message_json)
            print(f"  ✓ Message sent successfully via secure TLS connection")

            # Wait before sending next message
            if i < message_count - 1:  # Don't wait after last message
                await asyncio.sleep(interval_seconds)

        except Exception as e:
            print(f"  ✗ Error sending message: {e}")

    print()
    print(f"✓ Completed sending {message_count} messages")


async def main():
    """
    Main function to run the device simulator.
    """
    print("=" * 70)
    print("IoT Device Simulator - X.509 Certificate Authentication")
    print("=" * 70)
    print()

    # Check configuration
    check_configuration()

    # Create client with X.509 authentication
    client = create_x509_client()

    try:
        # Connect to IoT Hub
        print("Connecting to Azure IoT Hub...")
        await client.connect()
        print("✓ Connected successfully!")
        print()
        print("TLS Connection Established:")
        print("  • Server verified: Azure IoT Hub certificate checked")
        print("  • Client verified: Your device certificate authenticated")
        print("  • Encrypted channel: All data is now encrypted with TLS")
        print()

        # Send telemetry
        await send_telemetry(
            client,
            message_count=10,
            interval_seconds=5
        )

    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  • Verify IOTHUB_HOSTNAME is correct")
        print("  • Ensure device exists in IoT Hub with X.509 authentication")
        print("  • Check that certificate thumbprint matches in IoT Hub")
        print("  • Run 'python inspect_certificate.py' to get the correct thumbprint")

    finally:
        # Clean disconnect
        print()
        print("Disconnecting...")
        await client.disconnect()
        print("✓ Disconnected")
        print()
        print("=" * 70)
        print("Simulator completed")
        print("=" * 70)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 7):
        print("This script requires Python 3.7 or higher")
        sys.exit(1)

    # Run async main function
    asyncio.run(main())
