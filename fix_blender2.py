import re

with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'r') as f:
    content = f.read()

# Find the emotion_code section and replace it with a clean version
# The problem is the triple-quoted string inside the f-string template
# We need to find from 'emotion_code = ""' to the closing 'else: emotion_code = ""'

# Let's use a more targeted approach - find the specific section and replace
# The emotion_code block starts after robot_code and before sensor_init

# First, let's find the exact pattern
pattern = r'# Emotion Visualization\n        emotion_code = ""\n        if spec\.emotion_config:.*?else:\n                emotion_code = ""'

match = re.search(r'# Emotion Visualization.*?else:\n                emotion_code = ""', content, re.DOTALL)
if match:
    print("Found match")
    print("Length:", len(match.group()))
else:
    print("Pattern not found")

# Let's find the exact start and end positions
start = content.find('# Emotion Visualization')
end = content.find('\n                emotion_code = ""', content.find('# Emotion Visualization')) + len('\n                emotion_code = ""')

print(f"Start: {start}, End: {end}")

if start != -1 and end != -1:
    old_section = content[start:end]
    print("Old section length:", len(old_section))
    print(old_section[:300])
    print("---")
    print(old_section[-300:])