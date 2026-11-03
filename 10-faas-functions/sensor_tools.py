"""Tools that the AI agent can call: simulated IoT devices and their latest readings.

The same file is used by the Azure Function (function_app.py) and the AWS Lambda
function (aws/agent_function.py). Only the way the tools are passed to the model differs.
"""
import random
import time

# Instructions for the model, sent with every request
SYSTEM_PROMPT = (
    "You are an assistant for an IoT monitoring system. Answer questions about the devices "
    "and their sensor readings. Always use the tools to get the data - never guess values. "
    "A device is too hot when its temperature is above its max_temperature. "
    "Answer briefly, in plain text."
)

# The agent stops after this many model calls, so a confused model can't loop (and spend) forever
MAX_STEPS = 5

# Longest question the agent accepts
MAX_QUESTION_LENGTH = 500

# Simulated devices. In a real system this data would come from a database or an IoT service
DEVICES = {
    "device-01": {"location": "Server room", "max_temperature": 27.0, "base_temperature": 22.0},
    "device-02": {"location": "Greenhouse", "max_temperature": 30.0, "base_temperature": 32.5},
    "device-03": {"location": "Warehouse", "max_temperature": 25.0, "base_temperature": 18.0},
}

# Tool definitions: a name, a description for the model and a JSON schema of the input
TOOLS = [
    {
        "name": "list_devices",
        "description": "List all IoT devices with their ID and location.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_sensor_reading",
        "description": "Get the latest reading (temperature in C, humidity in %, pressure in hPa) "
                       "of one IoT device, together with the device's maximum allowed temperature.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "Device ID, for example device-01"}
            },
            "required": ["device_id"],
        },
    },
]


def list_devices():
    return {"devices": [{"device_id": device_id, "location": device["location"]}
                        for device_id, device in DEVICES.items()]}


def get_sensor_reading(device_id):
    device = DEVICES.get(device_id)
    if device is None:
        return {"error": f"Unknown device_id '{device_id}'. Use list_devices to get the valid IDs."}
    return {
        "device_id": device_id,
        "location": device["location"],
        "temperature": round(device["base_temperature"] + random.uniform(-1, 1), 1),
        "humidity": round(random.uniform(40, 60), 1),
        "pressure": round(random.uniform(990, 1030), 1),
        "max_temperature": device["max_temperature"],
        "timestamp": int(time.time()),
    }


def run_tool(name, tool_input):
    """Run the tool the model asked for. The model's input is untrusted, so it is checked first."""
    if not isinstance(tool_input, dict):
        return {"error": "The tool input must be a JSON object."}
    if name == "list_devices":
        return list_devices()
    if name == "get_sensor_reading":
        device_id = tool_input.get("device_id")
        if not isinstance(device_id, str):
            return {"error": "device_id must be a string."}
        return get_sensor_reading(device_id)
    return {"error": f"Unknown tool '{name}'."}
