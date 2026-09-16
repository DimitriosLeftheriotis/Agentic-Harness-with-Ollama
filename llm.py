import ast
import json
import re

from openai import OpenAI
from config import OLLAMA_BASE_URL, OLLAMA_API_KEY, DEFAULT_MODEL, DEFAULT_TEMPERATURE

# 1. Initialize the client using settings from config.py
client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY  # required by the client but unused by Ollama
)

# 2. System prompt tuned for 7B/14B Qwen models with Few-Shot demonstration
SYSTEM_PROMPT = """You are a coding agent that executes tasks by calling tools.

To use a tool, you MUST output ONLY a <tool_call> XML block with JSON. Do NOT write conversational text or python code blocks before the tool call.

Available Tools:
- read_file(path: str, offset: int = 1, limit: int = 60)
- write_file(path: str, content: str)
- str_replace(path: str, old_str: str, new_str: str)
- run_cmd(command: str)

EXAMPLE TURN:
User: Create a file named hello.py with print('hi')
Assistant:
<tool_call>
{"tool": "write_file", "args": {"path": "hello.py", "content": "print('hi')\\n"}}
</tool_call>

RULES:
- When you need to take an action, output ONLY the tool call.
- NEVER invent tool outputs yourself. Wait for execution results.
- When finished, reply with regular text.
"""

# 3. The LLM Caller Function
def generate_response(messages: list, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Sends the conversation history to Ollama and returns the generated text.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )

    return response.choices[0].message.content or ""

# 4. Multi-Format Tool Call Extractor (XML tags, JSON, & Native Python AST)
def extract_tool_call(response_text: str):
    """
    Extracts tool calls from:
    1. <tool_call>{JSON}</tool_call>
    2. Pure XML tags: <tool>name</tool><args><key>val</key></args>
    3. Raw JSON: {"tool": "...", "args": {...}}
    4. Python code blocks: write_file("...", "...")
    Returns: dict {"tool": "...", "args": {...}} or None.
    """
    # 1. Primary: Match <tool_call>{...}</tool_call>
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)", response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data and "args" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 2. Pure XML Tags: <tool>read_file</tool><args><path>llm.py</path></args>
    tool_tag_match = re.search(r"<tool>\s*(\w+)\s*</tool>", response_text)
    if tool_tag_match:
        tool_name = tool_tag_match.group(1).strip()
        args_dict = {}

        args_block_match = re.search(r"<args>\s*(.*?)\s*(?:</args>|$)", response_text, re.DOTALL)
        if args_block_match:
            args_content = args_block_match.group(1)
            param_matches = re.findall(r"<(\w+)>\s*(.*?)\s*</\1>", args_content, re.DOTALL)
            for param_name, param_val in param_matches:
                args_dict[param_name] = param_val.strip()

        if tool_name in ["read_file", "write_file", "str_replace", "run_cmd"]:
            return {"tool": tool_name, "args": args_dict}

    # 3. Fallback: Search for any JSON block containing "tool" and "args"
    json_match = re.search(r'(\{\s*"tool"\s*:\s*".*?"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})', response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if "tool" in data and "args" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 4. Fallback: Native Python AST Parsing (handles ```python ... ``` code blocks safely)
    code_text = response_text
    code_block_match = re.search(r"```(?:python)?\s*(.*?)\s*```", response_text, re.DOTALL)
    if code_block_match:
        code_text = code_block_match.group(1)

    try:
        tree = ast.parse(code_text.strip())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                tool_name = node.func.id
                if tool_name in ["read_file", "write_file", "str_replace", "run_cmd"]:
                    args_dict = {}
                    if tool_name == "write_file" and len(node.args) >= 2:
                        args_dict = {
                            "path": ast.literal_eval(node.args[0]),
                            "content": ast.literal_eval(node.args[1])
                        }
                    elif tool_name == "read_file" and len(node.args) >= 1:
                        args_dict = {"path": ast.literal_eval(node.args[0])}
                    elif tool_name == "run_cmd" and len(node.args) >= 1:
                        args_dict = {"command": ast.literal_eval(node.args[0])}
                    elif tool_name == "str_replace" and len(node.args) >= 3:
                        args_dict = {
                            "path": ast.literal_eval(node.args[0]),
                            "old_str": ast.literal_eval(node.args[1]),
                            "new_str": ast.literal_eval(node.args[2])
                        }
                    if args_dict:
                        return {"tool": tool_name, "args": args_dict}
    except Exception:
        pass

    return None