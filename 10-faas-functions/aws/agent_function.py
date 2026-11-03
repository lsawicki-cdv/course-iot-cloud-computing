"""AI agent on Amazon Bedrock: the model answers questions about IoT devices by calling tools.

The agent loop:
1. Send the question and the tool definitions to the model (Bedrock Converse API)
2. If the model asks for a tool (stopReason "tool_use"), run the tool and send the result back
3. Repeat until the model answers with text, or until MAX_STEPS model calls
"""
import logging
import os

import boto3
from botocore.config import Config

from sensor_tools import MAX_QUESTION_LENGTH, MAX_STEPS, SYSTEM_PROMPT, TOOLS, run_tool

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MODEL_ID = os.environ.get("MODEL_ID", "eu.amazon.nova-2-lite-v1:0")

bedrock = boto3.client("bedrock-runtime", config=Config(retries={"max_attempts": 5, "mode": "adaptive"}))

# The shared tool definitions in the format of the Bedrock Converse API
TOOL_CONFIG = {
    "tools": [{"toolSpec": {"name": tool["name"], "description": tool["description"],
                            "inputSchema": {"json": tool["parameters"]}}} for tool in TOOLS]
}


def ask_agent(question):
    messages = [{"role": "user", "content": [{"text": question}]}]
    steps = []

    for _ in range(MAX_STEPS):
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=TOOL_CONFIG,
            inferenceConfig={"maxTokens": 500, "temperature": 0},  # Always set maxTokens explicitly
        )
        message = response["output"]["message"]
        messages.append(message)

        if response["stopReason"] != "tool_use":
            answer = "".join(block.get("text", "") for block in message["content"])
            return {"answer": answer.strip(), "steps": steps}

        # The model asked for one or more tools: run them and send the results back
        tool_results = []
        for block in message["content"]:
            if "toolUse" not in block:
                continue
            tool_use = block["toolUse"]
            result = run_tool(tool_use["name"], tool_use["input"])
            logger.info("Tool %s(%s) -> %s", tool_use["name"], tool_use["input"], result)
            steps.append({"tool": tool_use["name"], "input": tool_use["input"], "result": result})
            tool_results.append({"toolResult": {"toolUseId": tool_use["toolUseId"], "content": [{"json": result}]}})
        messages.append({"role": "user", "content": tool_results})

    return {"answer": "The agent stopped after the maximum number of steps.", "steps": steps}


def lambda_handler(event, context):
    question = event.get("question") if isinstance(event, dict) else None
    if not isinstance(question, str) or not question.strip():
        return {"error": 'Send a question, for example {"question": "Is any device too hot?"}'}
    if len(question) > MAX_QUESTION_LENGTH:
        return {"error": f"The question is longer than {MAX_QUESTION_LENGTH} characters."}

    logger.info("Question: %s", question)
    result = ask_agent(question)
    logger.info("Answer: %s", result["answer"])
    return result
