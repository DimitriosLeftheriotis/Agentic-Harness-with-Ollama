import os                                                                                                                                               
import re                                                                                                                                               
                                                                                                                                                        
def is_safe_path(target_path: str, base_dir: str = None) -> bool:                                                                                       
    """                                                                                                                                                 
    Ensures target_path stays strictly inside the base_dir (sandbox).                                                                                   
    Prevents directory traversal attacks like '../../secret.txt'.                                                                                       
    """                                                                                                                                                 
    if base_dir is None:                                                                                                                                
        base_dir = os.getcwd()  # Current project folder                                                                                                
                                                                                                                                                        
    # Convert relative paths (like ../) into absolute physical disk paths                                                                               
    abs_base = os.path.abspath(base_dir)                                                                                                                
    abs_target = os.path.abspath(os.path.join(abs_base, target_path))                                                                                   
                                                                                                                                                        
    # Check if the target path starts with the project directory path                                                                                   
    return abs_target.startswith(abs_base) 


# List of regex patterns for destructive terminal commands across Windows and Linux                                                                  
DANGEROUS_PATTERNS = [                                                                                                                               
    r"\brm\s+-(?:r|f|rf|fr)\s+[/~]",       # Linux: rm -rf / or rm -rf ~                                                                             
    r"\bdel\s+/[sfq]\s+[c-zC-Z]:\\",       # Windows: del /s /q C:\                                                                                  
    r"\bformat\s+[c-zC-Z]:",               # Windows: format C:                                                                                      
    r"\bmkfs\b",                           # Linux: filesystem format                                                                                
    r"\bdd\s+if=",                         # Linux: raw disk overwrite                                                                               
    r"\bshutdown\b",                       # System shutdown                                                                                         
    r"\breboot\b",                         # System reboot                                                                                           
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", # Fork bomb (:(){ :|:& };:)                                                                         
    r"\bgit\s+reset\s+--hard\b",           # Git: wipes uncommitted work                                                                             
    r"\bgit\s+clean\s+-(?:f|fd|fdx)\b",    # Git: deletes untracked files                                                                            
    r"\bgit\s+push\s+.*--force\b",         # Git: destructive force push                                                                             
]                                                                                                                                                    
                                                                                                                                                        
def is_safe_command(command: str) -> tuple[bool, str]:                                                                                               
    """                                                                                                                                              
    Checks if a terminal command matches any known destructive patterns.                                                                             
    Returns: (is_safe: bool, reason: str)                                                                                                            
    """                                                                                                                                              
    cmd_clean = command.strip().lower()                                                                                                              
                                                                                                                                                        
    for pattern in DANGEROUS_PATTERNS:                                                                                                               
        if re.search(pattern, cmd_clean):                                                                                                            
            return False, f"⚠️ [Security Block]: Command matched dangerous pattern: '{pattern}'"                                                     
                                                                                                                                                        
    return True, ""                                   


# Interactive Approval Gate                                                                                                              
def check_permission(tool_name: str, args: dict, auto_approve_reads: bool = True) -> tuple[bool, str]:                                                                
    """                                                                                                                                                               
    Validates security constraints and prompts the user for confirmation if needed.                                                                                   
    """                                                                                                                                                               
    if tool_name not in ["read_file", "write_file", "str_replace", "run_cmd"]:                                                                                        
        return False, f"⚠️ [Security Error]: Unknown tool '{tool_name}'."                                                                                             
                                                                                                                                                                        
    if tool_name in ["read_file", "write_file", "str_replace"]:                                                                                                       
        path = args.get("path", "")                                                                                                                                   
        if not is_safe_path(path):                                                                                                                                    
            return False, f"⚠️ [Security Block]: Access denied. Path '{path}' escapes the project sandbox."                                                           
                                                                                                                                                                        
    if tool_name == "read_file" and auto_approve_reads:                                                                                                               
        return True, ""                                                                                                                                               
                                                                                                                                                                        
    if tool_name in ["write_file", "str_replace"]:                                                                                                                    
        path = args.get("path", "")                                                                                                                                   
        print(f"\n🛡️  [Security Gate] AI requests to modify: '{path}' using '{tool_name}'")                                                                           
        choice = input("    Allow this file change? [y/N]: ").strip().lower()                                                                                         
        if choice in ["y", "yes"]:                                                                                                                                    
            return True, ""                                                                                                                                           
        return False, f"⚠️ [User Rejected]: Permission denied by user for {tool_name} on '{path}'."                                                                   
                                                                                                                                                                        
    if tool_name == "run_cmd":                                                                                                                                        
        command = args.get("command", "")                                                                                                                             
                                                                                                                                                                        
        is_safe, reason = is_safe_command(command)                                                                                                                    
        if not is_safe:                                                                                                                                               
            return False, reason                                                                                                                                      
                                                                                                                                                                        
        print(f"\n🛡️  [Security Gate] AI requests to run command: '{command}'")                                                                                       
        choice = input("    Allow execution? [y/N]: ").strip().lower()                                                                                                
        if choice in ["y", "yes"]:                                                                                                                                    
            return True, ""                                                                                                                                           
        return False, f"⚠️ [User Rejected]: Permission denied by user to run '{command}'."                                                                            
                                                                                                                                                                        
    return False, "⚠️ [Security Error]: Unhandled permission state."