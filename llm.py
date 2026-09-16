import json
import re

from openai import OpenAI
from config import OLLAMA_BASE_URL, OLLAMA_API_KEY, DEFAULT_MODEL, DEFAULT_TEMPERATURE

# 1. Initialize the client using settings from config.py
client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key=OLLAMA_API_KEY  # required by the client but unused by Ollama
)

# 2. System prompt tuned for 7B/14B Qwen models
SYSTEM_PROMPT = """You are a precise coding agent working in the user's project directory.

When you need to take an action, output EXACTLY ONE tool call in this XML format:
<tool_call>
{"tool": "tool_name", "args": {"key": "value"}}
</tool_call>

Available Tools:
1. read_file(path: str, offset: int = 1, limit: int = 60)
    - Read lines of a file with line numbers.
2. write_file(path: str, content: str)
    - Create a new file or completely overwrite an existing one.
3. str_replace(path: str, old_str: str, new_str: str)
    - Replace an exact unique string in a file with new text.
4. run_cmd(command: str)
    - Execute a shell command in the current directory.

CRITICAL RULES:
- If you need to use a tool, start your response IMMEDIATELY with <tool_call>. Do NOT write conversational text before the tool call.
- Output ONLY ONE <tool_call> per message.
- STOP generating immediately after </tool_call>.
- NEVER invent or hallucinate tool output. Wait for the user/system to execute it.
- When you are finished or do not need a tool, reply with regular conversational text.
"""

# 3. The LLM Caller Function
def generate_response(messages: list, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> str:
    """
    Sends the conversation history to Ollama and returns the generated text.
    Enforces stop=["</tool_call>"] to prevent tool hallucination.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stop=["</tool_call>"]  # Hard stop at the end of the tool call
    )

    text = response.choices[0].message.content or ""

    # Ollama strips the stop sequence </tool_call> from the output.
    # We re-attach </tool_call> so our regex extractor has a complete tag.
    if "<tool_call>" in text and not text.strip().endswith("</tool_call>"):
        text = text.strip() + "\n</tool_call>"

    return text

# 4. The XML / JSON Tool Call Extractor
def extract_tool_call(response_text: str):
    """
    Extracts the tool call from <tool_call> tags OR fallback raw JSON blocks.
    Returns: dict {"tool": "...", "args": {...}} or None if no tool was called.
    """
    # 1. Primary: Match <tool_call>{...}</tool_call> (or unclosed tag)
    match = re.search(r"<tool_call>\s*(\{.*?\})\s*(?:</tool_call>|$)", response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "tool" in data and "args" in data:
                return data
        except json.JSONDecodeError:
            pass

    # 2. Fallback: Search for any JSON block containing "tool" and "args"
    json_match = re.search(r'(\{\s*"tool"\s*:\s*".*?"\s*,\s*"args"\s*:\s*\{.*?\}\s*\})', response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if "tool" in data and "args" in data:
                return data
        except json.JSONDecodeError:
            pass

    return None