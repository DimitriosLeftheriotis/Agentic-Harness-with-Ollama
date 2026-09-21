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

# 2. Concrete System prompt
SYSTEM_PROMPT = """You are a coding agent working in the user's project directory.

Available Tools:
1. read_file(path: str, offset: int = 1, limit: int = 100)
2. write_file(path: str, content: str)
3. str_replace(path: str, old_str: str, new_str: str)
4. run_cmd(command: str)

When you need to execute a tool, output XML using the real argument names:
Examples:
<tool>read_file</tool>
<args>
<path>llm.py</path>
</args>

To read beyond line 100 in a long file:
<tool>read_file</tool>
<args>
<path>llm.py</path>
<offset>101</offset>
</args>

<tool>run_cmd</tool>
<args>
<command>dir</command>
</args>

Rules:
- When you need to take an action, output the tool call.
- Use the exact argument names (path, offset, limit, content, old_str, new_str, command).
- Never invent tool outputs yourself.
- Do not repeatedly call the same tool with the exact same arguments.
- When asked to show, read, or inspect files, present the relevant code or content back to the user in markdown once you have read it.
- When finished or replying to the user, speak in regular conversational text.
"""

# 3. The LLM Caller Function
def generate_response(messages: list, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Sends the conversation history to Ollama and returns generated text.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )

    choice = response.choices[0]
    message = choice.message

    # 1. Check for Native Ollama / OpenAI Tool Calls
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        func_name = tool_call.function.name
        try:
            func_args = json.loads(tool_call.function.arguments)
        except Exception:
            func_args = {}
        return json.dumps({"tool": func_name, "args": func_args})

    # 2. Check for Text / XML / Fallback Content
    return message.content or ""


def normalize_tool_args(tool_name: str, args_dict: dict) -> dict:
    """
    Normalizes argument dictionaries from small models (like 7B) that may output
    <arg_name>path</arg_name><value>file.py</value> or generic parameter keys.
    """
    if not isinstance(args_dict, dict):
        return {}

    # Case 1: Model literally split <arg_name> and <value>
    if "arg_name" in args_dict and "value" in args_dict:
        k = args_dict.pop("arg_name").strip()
        v = args_dict.pop("value").strip()
        args_dict[k] = v

    # Case 2: Model output <arg_name>llm.py</arg_name> or generic keys
    if tool_name == "read_file":
        if "path" not in args_dict:
            for possible_key in ["arg_name", "file", "filename", "filepath", "value"]:
                if possible_key in args_dict:
                    args_dict["path"] = args_dict.pop(possible_key)
                    break
            if "path" not in args_dict and len(args_dict) == 1:
                args_dict["path"] = list(args_dict.values())[0]

        for offset_key in ["start", "start_line", "from_line"]:
            if offset_key in args_dict and "offset" not in args_dict:
                args_dict["offset"] = args_dict.pop(offset_key)

        for limit_key in ["lines", "count", "num_lines"]:
            if limit_key in args_dict and "limit" not in args_dict:
                args_dict["limit"] = args_dict.pop(limit_key)

    elif tool_name == "run_cmd" and "command" not in args_dict:
        for possible_key in ["cmd", "arg_name", "value"]:
            if possible_key in args_dict:
                args_dict["command"] = args_dict.pop(possible_key)
                break
        if "command" not in args_dict and len(args_dict) == 1:
            args_dict["command"] = list(args_dict.values())[0]

    elif tool_name == "write_file":
        if "path" not in args_dict:
            for possible_key in ["file", "filename", "filepath"]:
                if possible_key in args_dict:
                    args_dict["path"] = args_dict.pop(possible_key)
                    break
        if "content" not in args_dict:
            for possible_key in ["text", "code", "body", "value"]:
                if possible_key in args_dict:
                    args_dict["content"] = args_dict.pop(possible_key)
                    break

    return args_dict


# 4. Multi-Format Tool Call Extractor (XML tags, JSON, & Native Python AST)
def extract_tool_call(response_text: str):
    """
    Extracts tool calls from:
    1. Direct JSON: {"tool": "...", "args": {...}}
    2. Pure XML tags: <tool>name</tool><args><key>val</key></args>
    3. <tool_call>{JSON}</tool_call>
    4. Python code blocks: write_file("...", "...")
    Returns: dict {"tool": "...", "args": {...}} or None.
    """
    if not response_text:
        return None

    # 1. Direct JSON string
    try:
        data = json.loads(response_text.strip())
        if isinstance(data, dict) and "tool" in data and "args" in data:
            return {"tool": data["tool"], "args": normalize_tool_args(data["tool"], data["args"])}
    except (json.JSONDecodeError, ValueError):
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
            return {"tool": tool_name, "args": normalize_tool_args(tool_name, args_dict)}

    # 3. Match <tool_call>{...}</tool_call>
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)", response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data and "args" in data:
                return {"tool": data["tool"], "args": normalize_tool_args(data["tool"], data["args"])}
        except json.JSONDecodeError:
            pass

    # 4. Fallback: Search for any embedded JSON block containing "tool" and "args"
    json_match = re.search(r'(\{\s*"tool"\s*:\s*".*?"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})', response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if "tool" in data and "args" in data:
                return {"tool": data["tool"], "args": normalize_tool_args(data["tool"], data["args"])}
        except json.JSONDecodeError:
            pass

    # 5. Fallback: Native Python AST Parsing (handles ```python ... ``` code blocks safely)
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
                        if len(node.args) >= 2:
                            args_dict["offset"] = ast.literal_eval(node.args[1])
                        if len(node.args) >= 3:
                            args_dict["limit"] = ast.literal_eval(node.args[2])
                    elif tool_name == "run_cmd" and len(node.args) >= 1:
                        args_dict = {"command": ast.literal_eval(node.args[0])}
                    elif tool_name == "str_replace" and len(node.args) >= 3:
                        args_dict = {
                            "path": ast.literal_eval(node.args[0]),
                            "old_str": ast.literal_eval(node.args[1]),
                            "new_str": ast.literal_eval(node.args[2])
                        }

                    # Collect keyword args if present (e.g. read_file("llm.py", offset=61))
                    for kw in node.keywords:
                        try:
                            args_dict[kw.arg] = ast.literal_eval(kw.value)
                        except Exception:
                            pass

                    if args_dict:
                        return {"tool": tool_name, "args": normalize_tool_args(tool_name, args_dict)}
    except Exception:
        pass

    return None