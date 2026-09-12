import os                                                                                                                                                             
import subprocess                                                                                                                                                     
from config import COMMAND_TIMEOUT, MAX_OUTPUT_LINES                                                                                                                  
                                                                                                                                                                        
def truncate_output(text: str, max_lines: int = MAX_OUTPUT_LINES) -> str:                                                                                             
    """                                                                                                                                                               
    Truncates large text to protect the 7B/14B context window.                                                                                                        
    Keeps the first half and last half, summarizing the middle.                                                                                                       
    """                                                                                                                                                               
    lines = text.splitlines()                                                                                                                                         
    if len(lines) <= max_lines:                                                                                                                                       
        return text                                                                                                                                                   
                                                                                                                                                                        
    half = max_lines // 2                                                                                                                                             
    head = "\n".join(lines[:half])                                                                                                                                    
    tail = "\n".join(lines[-half:])                                                                                                                                   
    omitted = len(lines) - max_lines                                                                                                                                  
                                                                                                                                                                        
    return f"{head}\n\n... [{omitted} lines truncated to protect context] ...\n\n{tail}"     


def run_cmd(command: str) -> str:                                                                                                                                     
    """                                                                                                                                                               
    Executes a shell command with timeout protection.                                                                                                                 
    """                                                                                                                                                               
    try:                                                                                                                                                              
        result = subprocess.run(                                                                                                                                      
            command,                                                                                                                                                  
            shell=True,                                                                                                                                               
            capture_output=True,                                                                                                                                      
            text=True,                                                                                                                                                
            timeout=COMMAND_TIMEOUT  # From config.py (30 seconds)                                                                                                    
        )                                                                                                                                                             
                                                                                                                                                                        
        output = result.stdout + result.stderr                                                                                                                        
        output = output.strip() if output else "(Command executed with no output)"                                                                                    
                                                                                                                                                                        
        # Protect the context window from huge terminal dumps                                                                                                         
        return truncate_output(output)                                                                                                                                
                                                                                                                                                                        
    except subprocess.TimeoutExpired:                                                                                                                                 
        return f"⚠️ [Tool Error]: Command timed out after {COMMAND_TIMEOUT} seconds."                                                                                 
    except Exception as e:                                                                                                                                            
        return f"⚠️ [Tool Error]: {e}"