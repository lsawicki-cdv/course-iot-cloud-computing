## Azure Iot Hub

## Tested environments
Ubuntu 22.04
Python 3.10.12

### Prerequisites
```
pip3 install pipenv==2023.8.28
```

### Project packages installation
```bash
pipenv install
```

## Run simple MQTT client
```bash
pipenv run python simple_mqtt_device_simulator.py
```

1. Follow commands from `azure-cli-create-vm-mqtt.sh` in the Azure Cloud Shell
2. Receive and send MQTT messages locally
3. Test Python MQTT client `simple_mqtt_device_simulator.py`
4. Follow commands from `azure-cli-create-iot-hub.sh` in the Azure Cloud Shell
5. Test Python MQTT client `simple_mqtt_device_simulator.py`
6. Delete resource group