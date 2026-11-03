import random
import time
import json
import ssl
from paho.mqtt import client as mqtt


# Azure IoT Hub connection details
path_to_root_cert = "root_cert.pem"
device_id = "device-id"
sas_token = "device-sas-token"
iot_hub_name = "iot-hub-name"
mqtt_hub_hostname = "test.mosquitto.org"
mqtt_hub_port = 1883


def on_connect(client, userdata, flags, rc):
    print("Device connected with result code: " + str(rc))


def on_disconnect(client, userdata, rc):
    print("Device disconnected with result code: " + str(rc))


def on_publish(client, userdata, mid):
    print("Device sent message")


def on_subscribe(client, userdata, mid, granted_qos):
    print("Topic subscribed!")


def on_message(client, userdata, msg):
    print("Received message!\n")
    print("Topic: '" + msg.topic+"', payload: " + str(msg.payload))


def simulate_device():

    client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv311)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    # Azure IoT Hub connection details
    # print(iot_hub_name+".azure-devices.net/" +
    #       device_id + "/?api-version=2021-04-12")
    # client.username_pw_set(username=iot_hub_name+".azure-devices.net/" +
    #                        device_id + "/?api-version=2021-04-12", password=sas_token)

    # client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None,
    #                cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
    # client.tls_insecure_set(False)

    print("Connecting MQTT broker")
    client.connect(mqtt_hub_hostname, port=mqtt_hub_port)

    print("Connected to MQTT broker")

    topic = "devices/" + device_id + "/messages/events/"
    print(f"MQTT topic: {topic}")

    while True:
        # Generate random sensor data
        temperature = random.uniform(20, 30)
        humidity = random.uniform(40, 60)
        pressure = random.uniform(900, 1100)

        # Send data to IoT hub
        send_data_to_iot_hub(client, temperature, humidity, pressure, topic)

        # Wait for some time before sending the next data
        time.sleep(10)


def send_data_to_iot_hub(device_client, temperature, humidity, pressure, topic):
    payload = {
        "device_id": device_id,
        "temperature": temperature,
        "humidity": humidity,
        "pressure": pressure,
        "timestamp": time.time()
    }
    message = json.dumps(payload)
    device_client.publish(topic, message, qos=1)
    print(f"Message sent: {message}")


# Start simulating the device
simulate_device()
