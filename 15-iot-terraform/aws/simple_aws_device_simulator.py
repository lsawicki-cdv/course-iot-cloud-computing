import random
import time
import json
import ssl
from paho.mqtt import client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties


# AWS IoT Core connection details
path_to_root_cert = "AmazonRootCA1.pem"
path_to_device_cert = "device.pem.crt"
path_to_private_key = "private.pem.key"
device_id = "terraform-device-01"
iot_endpoint = "iot_endpoint"  # e.g. a1b2c3d4e5f6g7-ats.iot.eu-west-2.amazonaws.com
iot_port = 8883


def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected to AWS IoT with result code: " + str(reason_code))


def simulate_device():
    # MQTT 5: the version of MQTT with user properties (the counterpart of custom properties in Azure IoT Hub)
    client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv5)
    client.on_connect = on_connect

    # The device authenticates with its certificate, no username or password
    client.tls_set(ca_certs=path_to_root_cert, certfile=path_to_device_cert, keyfile=path_to_private_key,
                   cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)

    print("Connecting to AWS IoT")
    client.connect(iot_endpoint, port=iot_port)
    # Start the network loop in the background: it handles the connection, acknowledgements and callbacks
    client.loop_start()

    topic = "devices/" + device_id + "/messages/events/"
    print(f"MQTT topic: {topic}")

    while True:
        # Generate random sensor data
        temperature = random.uniform(20, 30)
        humidity = random.uniform(40, 60)
        pressure = random.uniform(900, 1100)

        # Send data to IoT Core
        send_data_to_iot_core(client, temperature, humidity, pressure, topic)

        # Wait for some time before sending the next data
        time.sleep(10)


def send_data_to_iot_core(client, temperature, humidity, pressure, topic):
    payload = {
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure
    }
    message = json.dumps(payload)
    properties = Properties(PacketTypes.PUBLISH)
    properties.ContentType = "application/json"
    properties.UserProperty = ("level", "storage")
    client.publish(topic, message, qos=1, properties=properties)
    print(f"Message sent: {message}")


# Start simulating the device
simulate_device()
