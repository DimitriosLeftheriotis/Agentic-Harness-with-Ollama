import os

# 1. Where does Ollama live?
# On your machine, Ollama exposes an OpenAI-compatible API at http://localhost:11434/v1
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = "ollama"  # Ollama doesn't require a real key, but the client expects a string

# 2. Which model to use?
# Recommended: "qwen2.5-coder:14b" (if on Lab PC / strong GPU) or "qwen2.5-coder:7b" (on laptop)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5-coder:7b")

# 3. Model parameters
# Low temperature (0.1) makes tool calling deterministic rather than creative
DEFAULT_TEMPERATURE = 0.1

# 4. Tool Execution Settings
COMMAND_TIMEOUT = 30  # Max seconds for a shell command before killing it
MAX_OUTPUT_LINES = 60  # Truncate tool output if it exceeds 60 lines