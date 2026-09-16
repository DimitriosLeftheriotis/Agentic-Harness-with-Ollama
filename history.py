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
