# 🤖 Agentic Harness with Ollama

A lightweight, fully transparent AI coding agent that runs **locally** using [Ollama](https://ollama.ai) and small open-source models (7B/14B parameters).

Built from scratch without heavy frameworks and cloud dependencies.

## Why This Exists

Large agent frameworks (LangChain, CrewAI, etc.) are designed for cloud APIs and 70B+ models. When you run them with small local models (7B/14B), the models:
- Hallucinate fake tool outputs instead of actually calling tools
- Dump raw JSON into chat instead of using structured tool calls
- Get confused by complex prompt formats with reserved control tokens

This harness strips everything down to the minimum a small model needs to work reliably as a coding agent.

## Features

- **4 core tools**: `read_file`, `write_file`, `str_replace`, `run_cmd`
- **3-tier security**: Auto-approve reads → prompt for writes → prompt + danger-check for shell commands
- **Robust tool parsing**: 5 fallback extraction methods (JSON → XML → tool_call tags → embedded JSON → Python AST)
- **Argument normalization**: Automatically fixes mangled argument names from 7B models
- **Context management**: Sliding-window history pruning to prevent context overflow
- **Session persistence**: Conversations save to disk and resume on restart
- **Loop protection**: Duplicate call guard + max step limit prevent infinite loops
- **Sandbox enforcement**: Path containment prevents directory traversal attacks

## Architecture

```
config.py        → Settings (model, endpoint, timeouts)
llm.py           → System prompt, LLM caller, tool call parser
tools.py         → Tool implementations (read, write, replace, run terminal commands)
permissions.py   → Security gates (path sandbox, command filter, user approval)
history.py       → Conversation history with pruning and persistence
agent.py         → Interactive CLI REPL with agentic tool loop
```

## Quick Start

### Prerequisites
- [Python 3.10+](https://python.org)
- [Ollama](https://ollama.ai) running locally with a model pulled

### Install & Run

```bash
# Clone the repo
git clone https://github.com/DimitriosLeftheriotis/Agentic-Harness-with-Ollama.git
cd Agentic-Harness-with-Ollama

# Install dependencies
pip install -r requirements.txt

# Pull a model (if you haven't already)
ollama pull qwen2.5-coder:7b

# Run the agent
python agent.py
```

### Configuration

Edit `config.py` to change:
- **Model**: Set `DEFAULT_MODEL` (e.g. `qwen2.5-coder:7b`, `qwen2.5-coder:14b`)
- **Endpoint**: Set `OLLAMA_BASE_URL` if Ollama isn't on `localhost:11434`
- **Temperature**: Lower = more deterministic tool calls, higher = more creative responses

You can also set these via environment variables:
```bash
DEFAULT_MODEL=qwen2.5-coder:14b python agent.py
```

## Usage

```
You > show me the contents of config.py

⚙️  [Running read_file]: {'path': 'config.py'}
📄 [Output]:
--- File: config.py (Showing lines 1-19 of 19 [End of file]) ---
   1 | import os
   ...

Agent > Here are the contents of config.py: ...

You > create a file called hello.py that prints "Hello World"

🛡️  [Security Gate] AI requests to modify: 'hello.py' using 'write_file'
    Allow this file change? [y/N]: y

⚙️  [Running write_file]: {'path': 'hello.py', 'content': 'print("Hello World")\n'}
📄 [Output]:
✅ Successfully wrote 1 lines (22 bytes) to 'hello.py'.

You > exit
👋 Saving session. Goodbye!
```

## Commands

| Command | What it does |
|---------|-------------|
| `exit` / `quit` | Save session and exit |
| `clear` / `reset` | Wipe conversation memory and start fresh |
| `Ctrl+C` | Cancel current operation and return to prompt |

## License

MIT
