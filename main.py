from openai import OpenAI
import subprocess
import json

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # required by the client but unused by Ollama
)

user_input = input("Enter your prompt > ")

SYSTEM_PROMPT = """
You are a coding agent. Your job is to code. Always code.
Use the bash tool to inpect files.
"""

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run"
                }
            },
            "required": ["command"],
        },
    },
}

def bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

response = client.chat.completions.create(
    model="qwen2.5-coder:7b",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ],
    tools=[BASH_TOOL],
)

message = response.choices[0].message

completion_details = response.usage.completion_tokens_details
prompt_details = response.usage.prompt_tokens_details

usage = {
    "prompt_tokens": response.usage.prompt_tokens,
    "completion_tokens": response.usage.completion_tokens,
    "reasoning_tokens": getattr(completion_details, "reasoning_tokens", None),
    "cached_tokens": getattr(prompt_details, "cached_tokens", None)
}

# Check for proper tool calls first
if message.tool_calls:
    for tool_call in message.tool_calls:
        args = json.loads(tool_call.function.arguments)
        print(f"\nTool call: {tool_call.function.name}({args['command']})")
        result = bash(args["command"])
        print(f"Result:\n{result}")
# Fallback: model may embed tool call as JSON in content
elif message.content:
    try:
        tool_call_data = json.loads(message.content)
        if "name" in tool_call_data and "arguments" in tool_call_data:
            args = tool_call_data["arguments"]
            print(f"\nTool call (parsed from content): {tool_call_data['name']}({args['command']})")
            result = bash(args["command"])
            print(f"Result:\n{result}")
        else:
            print("\nAgent: ", message.content, "\n")
    except (json.JSONDecodeError, KeyError):
        print("\nAgent: ", message.content, "\n")

print(usage)
