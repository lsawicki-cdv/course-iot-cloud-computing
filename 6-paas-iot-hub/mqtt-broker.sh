#!/bin/bash

# Pull the Eclipse Mosquitto image
docker pull eclipse-mosquitto

# Run the MQTT broker in a Docker container
docker run --rm --name mqtt-broker -p 1883:1883 -v $PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto

# Subscribe to the topic 'test/topic'
docker run --rm --network host eclipse-mosquitto mosquitto_sub -h localhost -p 1883 -t test/topic

# Publish a message to the topic 'test/topic'
docker run --rm --network host eclipse-mosquitto mosquitto_pub -h localhost -p 1883 -t test/topic -m "Hello MQTT from VM"

# Run an interactive terminal in the Docker container
# docker run -it --rm eclipse-mosquitto /bin/sh

# Expose docker container to the internet using ngrok
ngrok tcp 1883

# Publish from VM via ngrok
docker run --rm --network host eclipse-mosquitto mosquitto_pub -h 0.tcp.eu.ngrok.io -p 10451 -t test/topic -m "Hello MQTT from VM"