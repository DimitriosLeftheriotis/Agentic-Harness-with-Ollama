from tools import write_file, read_file, str_replace, run_cmd

print("--- 1. Testing write_file ---")
print(write_file("test.txt", "Hello World\nLine 2\nLine 3"))

print("\n--- 2. Testing read_file ---")
print(read_file("test.txt"))

print("\n--- 3. Testing str_replace ---")
print(str_replace("test.txt", "Line 2", "Modified Line"))

print("\n--- 4. Reading after edit ---")
print(read_file("test.txt"))

print("\n--- 5. Testing run_cmd ---")
print(run_cmd("echo All tools are working!"))
