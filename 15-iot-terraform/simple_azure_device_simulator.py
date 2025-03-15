import random
import time
import json
from azure.iot.device import IoTHubDeviceClient, Message


def simulate_device():

    conn_str = "connection_string"
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    print("Connecting to Azure IoT")
    device_client.connect()
    print("Connected to Azure IoT")
    while True:
        # Generate random sensor data
        temperature = random.uniform(20, 30)
        humidity = random.uniform(40, 60)
        pressure = random.uniform(900, 1100)

        # Send data to IoT hub
        send_data_to_iot_hub(device_client, temperature, humidity, pressure)

        # Wait for some time before sending the next data
        time.sleep(10)


def send_data_to_iot_hub(device_client, temperature, humidity, pressure):
    payload = {
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure
    }
    message = Message(json.dumps(payload))
    message.content_type = "application/json"
    message.content_encoding = "utf-8"
    message.custom_properties["level"] = "storage"
    device_client.send_message(message)
    print(f"Message sent: {message}")


# Start simulating the device
simulate_device()
