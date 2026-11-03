"""Run the Lambda functions on your own computer or in AWS CloudShell, without deploying them.

python3 test_locally.py hello Student
python3 test_locally.py agent "Is any device too hot?"
"""
import json
import os
import sys

# sensor_tools.py is in this folder (CloudShell) or in the parent folder (the course repository)
here = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([here, os.path.dirname(here)])

if len(sys.argv) != 3 or sys.argv[1] not in ("hello", "agent"):
    sys.exit(__doc__)

if sys.argv[1] == "hello":
    from lambda_function import lambda_handler
    # The same event a function URL sends for GET ...?name=<name>
    event = {"queryStringParameters": {"name": sys.argv[2]}}
else:
    from agent_function import lambda_handler
    event = {"question": sys.argv[2]}

print(json.dumps(lambda_handler(event, None), indent=2, ensure_ascii=False))
