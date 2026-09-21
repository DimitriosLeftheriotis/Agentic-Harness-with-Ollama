import json                                                                                                                                                           
import os                                                                                                                                                             
from llm import SYSTEM_PROMPT                                                                                                                                         
                                                                                                                                                                        
SESSION_FILE = ".session.json"                                                                                                                                        
                                                                                                                                                                        
class ConversationHistory:                                                                                                                                            
    def __init__(self):                                                                                                                                               
        self.messages = []                                                                                                                                            
        self.reset()                                                                                                                                                  
                                                                                                                                                                        
    def reset(self):                                                                                                                                                  
        """Resets the history with the base system prompt."""                                                                                                         
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]                                                                                                
                                                                                                                                                                        
    def add_user_message(self, content: str):                                                                                                                         
        self.messages.append({"role": "user", "content": content})                                                                                                    
                                                                                                                                                                        
    def add_assistant_message(self, content: str):                                                                                                                    
        self.messages.append({"role": "assistant", "content": content})                                                                                               
                                                                                                                                                                        
    def add_tool_result(self, tool_name: str, result: str):                                                                                                           
        """Feeds the tool execution output back to the model as a user turn."""                                                                                       
        formatted_result = f"⚙️ [Tool Result from {tool_name}]:\n{result}"                                                                                            
        self.messages.append({"role": "user", "content": formatted_result})       



    def save_session(self, filepath: str = SESSION_FILE) -> bool:
                """
                Saves the current conversation history to disk as a JSON file.
                """
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(self.messages, f, indent=2, ensure_ascii=False)
                    return True
                except Exception as e:
                    print(f"⚠️ [History Warning]: Failed to save session to '{filepath}': {e}")
                    return False

    def load_session(self, filepath: str = SESSION_FILE) -> bool:
        """
        Loads a previous conversation history from disk if it exists.
        Returns True if loaded successfully, False otherwise.
        """
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list) and len(data) > 0:
                self.messages = data
                return True
            return False

        except Exception as e:
            print(f"⚠️ [History Warning]: Failed to load session from '{filepath}': {e}")
            return False

    def prune_history(self, max_messages: int = 14):
                """
                Compacts older intermediate tool outputs and limits message stack size
                to keep the model fast and prevent context overflow.
                """
                if len(self.messages) <= max_messages:
                    return

                # 1. Always keep the System Prompt (Index 0)
                system_msg = self.messages[0]

                # 2. Grab the most recent messages (Active Working Context)
                recent_messages = self.messages[-(max_messages - 1):]

                # 3. Compact older tool outputs inside the recent history if they are bulky
                for msg in recent_messages[:-3]:  # Leave the last 3 turns completely untouched
                    if msg.get("role") == "user" and "⚙️ [Tool Result from" in msg.get("content", ""):
                        lines = msg["content"].splitlines()
                        if len(lines) > 5:
                            # Summarize old tool results to just the header line
                            msg["content"] = lines[0] + "\n(Output compacted to save context window)"

                # 4. Reconstruct the message stack: System Prompt + Compacted Recent Messages
                self.messages = [system_msg] + recent_messages

