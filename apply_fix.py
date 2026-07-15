import re

with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'r') as f:
    content = f.read()

# Read the new emotion code
with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\emotion_code.py', 'r') as f:
    new_emotion_code = f.read()

# Find the old emotion_code section
# It starts with "# Emotion Visualization" and ends before "# Sensor init"
start = content.find("# Emotion Visualization")
if start == -1:
    print("Could not find emotion section")
else:
    # Find the end - "else:\n                emotion_code = \"\""
    end = content.find("else:\n                emotion_code = \"\"", start)
    if end == -1:
        print("Could not find end marker")
    else:
        end += len('else:\n                emotion_code = ""')
        print(f"Found section from {start} to {end}")

        # Replace
        new_content = content[:start] + new_emotion_code + content[end:]
        
        with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'w') as f:
            f.write(new_content)
        print("Fixed!")