with open(r'C:\Users\subur\Documents\New OpenCode Project\web-crawler-agent\src\crawler_agent\cognitive\blender_sandbox.py', 'r') as f:
    content = f.read()

# Count triple quotes
double_count = content.count('"""')
single_count = content.count("'''")
print('Triple double quotes:', double_count)
print('Triple single quotes:', single_count)

# Find unmatched triple quotes
import re
for m in re.finditer(r'"""', content):
    start = max(0, m.start() - 50)
    end = min(len(content), m.end() + 50)
    context = content[start:end].replace('\n', '\\n')
    print(f'Triple double at {m.start()}: ...{content[start:end].replace(chr(10), "\\n")}...')

for m in re.finditer(r"'''", content):
    start = max(0, m.start() - 50)
    end = min(len(content), m.end() + 50)
    context = content[start:end].replace('\n', '\\n')
    print(f'Triple single at {m.start()}: ...{content[start:end].replace(chr(10), "\\n")}...')