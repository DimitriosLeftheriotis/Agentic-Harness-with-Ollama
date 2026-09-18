import sys
# Force modern UTF-8 encoding in Windows console
sys.stdout.reconfigure(encoding="utf-8")

import json
import re
from config import DEFAULT_MODEL, OLLAMA_BASE_URL
from llm import generate_response, extract_tool_call
from tools import TOOL_REGISTRY
from permissions import check_permission
from history import ConversationHistory

def main():
    history = ConversationHistory()

    # Try to resume past conversation if available
    if history.load_session():
        print(f"🔄 Resumed previous session ({len(history.messages)} messages loaded).")
        print("   (Type 'clear' to start a brand new conversation)\n")

    print("=" * 60)
    print(f"🤖 LOCAL AGENT ONLINE | Model: {DEFAULT_MODEL}")
    print(f"🔗 Endpoint: {OLLAMA_BASE_URL}")
    print("🛡️  Guardrails: Sandboxed to working directory | [y/N] for edits")
    print("Commands: 'exit' to quit | 'clear' to reset memory")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            history.save_session()
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("👋 Saving session. Goodbye!")
            history.save_session()
            break

        if user_input.lower() in ["clear", "reset"]:
            history.reset()
            history.save_session()
            print("🧹 Conversation memory cleared. Starting fresh session!\n")
            continue

        history.add_user_message(user_input)

        try:
            # --- INNER AGENTIC LOOP ---
            step_count = 0
            last_tool_call = None

            while True:
                step_count += 1
                history.prune_history()

                print(f"\n🤔 Agent is thinking (step {step_count})...", end="", flush=True)
                try:
                    response_text = generate_response(history.messages)
                except Exception as e:
                    print("\r" + " " * 45 + "\r", end="", flush=True)
                    print(f"\n⚠️ [Ollama Server Error]: {e}")
                    print("   Please ensure Ollama is running and responsive, then try your prompt again.")
                    break

                print("\r" + " " * 45 + "\r", end="", flush=True)

                tool_data = extract_tool_call(response_text)

                # CASE A: The Model Called a Tool
                if tool_data and "tool" in tool_data and tool_data["tool"] in TOOL_REGISTRY:
                    tool_name = tool_data["tool"]
                    args = tool_data.get("args", {})

                    # DUPLICATE CALL GUARD: Stop identical tool calls in consecutive steps
                    current_call = (tool_name, json.dumps(args, sort_keys=True))
                    if current_call == last_tool_call:
                        history.add_assistant_message(response_text)
                        result = f"⚠️ [Loop Prevented]: You already executed '{tool_name}' with these exact arguments ({args}). Do not repeat the same call. If you need more lines, change the offset. Otherwise, synthesize your findings and present your answer to the user."
                        print(f"\n🔁 {result}\n")
                        history.add_tool_result(tool_name, result)
                        history.save_session()
                        continue

                    last_tool_call = current_call

                    history.add_assistant_message(response_text)

                    is_allowed, message = check_permission(tool_name, args)

                    if not is_allowed:
                        result = message
                        print(f"\n🛑 {result}")
                    else:
                        print(f"\n⚙️  [Running {tool_name}]: {args}")
                        func = TOOL_REGISTRY[tool_name]
                        try:
                            result = func(**args)
                        except TypeError as e:
                            result = f"⚠️ [Argument Error]: {e}"

                        # Print the full tool output to the terminal so the user sees the real code/output!
                        print(f"\n📄 [Output]:\n{result.strip()}\n")

                    history.add_tool_result(tool_name, result)
                    history.save_session()
                    continue

                # CASE B: Normal Text Response (Task Complete)
                else:
                    history.add_assistant_message(response_text)
                    history.save_session()

                    # Clean only dangling tool tags, preserving all markdown and code blocks
                    clean_reply = re.sub(r"<tool_call>.*?</tool_call>|<tool>.*?</args>", "", response_text, flags=re.DOTALL).strip()
                    final_text = clean_reply if clean_reply else response_text.strip()
                    if final_text:
                        print(f"\nAgent > {final_text}")
                    else:
                        print(f"\nAgent > (Empty response from model. Raw text: {repr(response_text)})")
                    break
        except KeyboardInterrupt:
            print("\r" + " " * 45 + "\r", end="", flush=True)
            print("\n🛑 Operation interrupted by user (Ctrl+C). Returning to prompt.")
            history.save_session()
            continue

if __name__ == "__main__":
    main()