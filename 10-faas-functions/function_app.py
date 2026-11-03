# function_app.py
import azure.functions as func
import json
import logging
import os

from sensor_tools import MAX_QUESTION_LENGTH, MAX_STEPS, SYSTEM_PROMPT, TOOLS, run_tool

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="HttpTrigger1")
@app.route(route="hello")
def test_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP-triggered function executed successfully.")
    else:
        return func.HttpResponse(
            "This HTTP-triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
            status_code=200
        )


# AI agent (Part 5): the model answers questions about IoT devices by calling the tools from sensor_tools.py.
# The loop: send the question and the tools to the model, run the tools it asks for, send the results back,
# and repeat until the model answers with text (or until MAX_STEPS model calls).
def ask_agent(question):
    from openai import OpenAI  # Imported here, so the hello function works without the AI settings

    # Azure OpenAI in Foundry Models, through the OpenAI-compatible v1 API
    client = OpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/openai/v1/",
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )
    # The shared tool definitions in the format of the Chat Completions API
    tools = [{"type": "function", "function": tool} for tool in TOOLS]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    steps = []

    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=os.environ["AZURE_OPENAI_DEPLOYMENT"],  # The name of your model deployment
            messages=messages,
            tools=tools,
            max_completion_tokens=500,  # Always limit the answer's length
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return {"answer": (message.content or "").strip(), "steps": steps}

        # The model asked for one or more tools: run them and send the results back
        for tool_call in message.tool_calls:
            try:
                tool_input = json.loads(tool_call.function.arguments or "{}")
            except ValueError:
                tool_input = None
            result = run_tool(tool_call.function.name, tool_input)
            logging.info("Tool %s(%s) -> %s", tool_call.function.name, tool_input, result)
            steps.append({"tool": tool_call.function.name, "input": tool_input, "result": result})
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

    return {"answer": "The agent stopped after the maximum number of steps.", "steps": steps}


@app.function_name(name="AgentTrigger")
@app.route(route="agent", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def agent_function(req: func.HttpRequest) -> func.HttpResponse:
    try:
        question = req.get_json().get("question")
    except (ValueError, AttributeError):
        question = None
    if not isinstance(question, str) or not question.strip():
        return func.HttpResponse('Send a question, for example {"question": "Is any device too hot?"}', status_code=400)
    if len(question) > MAX_QUESTION_LENGTH:
        return func.HttpResponse(f"The question is longer than {MAX_QUESTION_LENGTH} characters.", status_code=400)

    missing = [name for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
               if not os.environ.get(name)]
    if missing:
        return func.HttpResponse(f"Missing settings: {', '.join(missing)} (see Step 19 of the readme)", status_code=500)

    logging.info("Question: %s", question)
    result = ask_agent(question)
    logging.info("Answer: %s", result["answer"])
    return func.HttpResponse(json.dumps(result), mimetype="application/json")
