import os                                                                                                                                                             
import subprocess                                                                                                                                                     
from config import COMMAND_TIMEOUT, MAX_OUTPUT_LINES                                                                                                                  
                                                                                                                                                                        
def truncate_output(text: str, max_lines: int = MAX_OUTPUT_LINES) -> str:                                                                                             
    """                                                                                                                                                               
    Truncates large text to protect context window.                                                                                                        
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
            errors="replace",                                                                                                                                         
            timeout=COMMAND_TIMEOUT  # From config.py (30 seconds)                                                                                                    
        )                                                                                                                                                             
                                                                                                                                                                        
        stdout = result.stdout or ""                                                                                                                                  
        stderr = result.stderr or ""                                                                                                                                  
        output = (stdout + "\n" + stderr).strip() if stderr else stdout.strip()                                                                                       
        output = output if output else "(Command executed with no output)"                                                                                    
                                                                                                                                                                        
        # Protect the context window from huge terminal dumps                                                                                                         
        return truncate_output(output)                                                                                                                                
                                                                                                                                                                        
    except subprocess.TimeoutExpired:                                                                                                                                 
        return f"⚠️ [Tool Error]: Command timed out after {COMMAND_TIMEOUT} seconds."                                                                                 
    except Exception as e:                                                                                                                                            
        return f"⚠️ [Tool Error]: {e}"


def read_file(path: str, offset: int = 1, limit: int = 100) -> str:
    try:
        offset = int(offset)
        limit = int(limit)
        if not os.path.exists(path):
            return f"⚠️ [Tool Error]: File '{path}' does not exist."

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if total_lines == 0:
            return f"(File '{path}' is empty)"

        start_idx = max(0, offset - 1)
        end_idx = min(total_lines, start_idx + limit)
        selected_lines = lines[start_idx:end_idx]

        output = []
        for i, line in enumerate(selected_lines, start=start_idx + 1):
            output.append(f"{i:4d} | {line}")

        if end_idx < total_lines:
            header = f"--- File: {path} (Showing lines {start_idx + 1}-{end_idx} of {total_lines}. Next offset: {end_idx + 1}) ---\n"
        else:
            header = f"--- File: {path} (Showing lines {start_idx + 1}-{end_idx} of {total_lines} [End of file]) ---\n"

        return header + "".join(output)

    except Exception as e:
        return f"⚠️ [Tool Error reading '{path}']: {e}"


def write_file(path: str, content: str) -> str:                                                                                                                                                                                                                     
        try:                                                                                                                                                                                                                                                            
            parent_dir = os.path.dirname(path)                                                                                                                                                                                                                          
            if parent_dir and not os.path.exists(parent_dir):                                                                                                                                                                                                           
                os.makedirs(parent_dir, exist_ok=True)                                                                                                                                                                                                                  
                                                                                                                                                                                                                                                                        
            with open(path, "w", encoding="utf-8") as f:                                                                                                                                                                                                                
                f.write(content)                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                        
            line_count = len(content.splitlines())                                                                                                                                                                                                                      
            byte_count = len(content.encode("utf-8"))                                                                                                                                                                                                                   
            return f"✅ Successfully wrote {line_count} lines ({byte_count} bytes) to '{path}'."                                                                                                                                                                        
                                                                                                                                                                                                                                                                        
        except Exception as e:                                                                                                                                                                                                                                          
            return f"⚠️ [Tool Error writing to '{path}']: {e}"


def str_replace(path: str, old_str: str, new_str: str) -> str:                                                                                                                                                                                                      
        try:                                                                                                                                                                                                                                                            
            if not os.path.exists(path):                                                                                                                                                                                                                                
                return f"⚠️ [Tool Error]: File '{path}' does not exist."                                                                                                                                                                                                
                                                                                                                                                                                                                                                                        
            with open(path, "r", encoding="utf-8", errors="replace") as f:                                                                                                                                                                                              
                content = f.read()                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                        
            # 1. Check if the target text actually exists                                                                                                                                                                                                               
            count = content.count(old_str)                                                                                                                                                                                                                              
            if count == 0:                                                                                                                                                                                                                                              
                return f"⚠️ [Tool Error]: The specified old_str was not found in '{path}'. Make sure the indentation and wording match the file exactly."                                                                                                               
                                                                                                                                                                                                                                                                        
            # 2. Check for uniqueness to prevent accidental edits                                                                                                                                                                                                       
            if count > 1:                                                                                                                                                                                                                                               
                return f"⚠️ [Tool Error]: The specified old_str appears {count} times in '{path}'. Please include more surrounding context lines so the target is unique."                                                                                              
                                                                                                                                                                                                                                                                        
            # 3. Perform the single replacement                                                                                                                                                                                                                         
            new_content = content.replace(old_str, new_str, 1)                                                                                                                                                                                                          
                                                                                                                                                                                                                                                                        
            with open(path, "w", encoding="utf-8") as f:                                                                                                                                                                                                                
                f.write(new_content)                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                        
            return f"✅ Successfully updated '{path}'."                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                        
        except Exception as e:                                                                                                                                                                                                                                          
            return f"⚠️ [Tool Error editing '{path}']: {e}"     


# --- The Tool Registry ---                                                                                                                                                                                                               
# Maps tool names (from XML tags) to the actual Python functions                                                                                                                                                                             
TOOL_REGISTRY = {                                                                                                                                                                                                                            
    "read_file": read_file,                                                                                                                                                                                                                  
    "write_file": write_file,                                                                                                                                                                                                                
    "str_replace": str_replace,                                                                                                                                                                                                              
    "run_cmd": run_cmd                                                                                                                                                                                                                       
}                       