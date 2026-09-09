from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # required by the client but unused by Ollama
)

user_input = input("Enter your prompt > ")

SYSTEM_PROMPT = """
You are a coding agent. Your job is to code. Always code.
"""

response = client.chat.completions.create(
    model="qwen2.5:1.5b",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]
)

output = response.choices[0].message.content

completion_details = response.usage.completion_tokens_details
prompt_details = response.usage.prompt_tokens_details

usage = {
    "prompt_tokens": response.usage.prompt_tokens,
    "completion_tokens": response.usage.completion_tokens,
    "reasoning_tokens": getattr(completion_details, "reasoning_tokens", None),
    "cached_tokens": getattr(prompt_details, "cached_tokens", None)
}

print("\nAgent: ", output, "\n")
print(usage)
