"""Replace HTML block and update window size in deepseek_monitor.py"""
import os

BASE = r'C:\Users\寻逆啊\Claude'

# Read new UI content
with open(os.path.join(BASE, 'new_ui.html'), 'r', encoding='utf-8') as f:
    new_html_content = f.read()

# Read the target file
target = os.path.join(BASE, 'deepseek_monitor.py')
with open(target, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the HTML variable assignment boundaries
start_marker = "HTML = r'''"
end_marker = "</script></body></html>'''"

start = content.find(start_marker)
end = content.find(end_marker, start) + len(end_marker)

if start == -1 or end == -1:
    print('ERROR: Could not find HTML block boundaries')
    print('start:', start, 'end:', end)
    exit(1)

# Construct new HTML variable assignment
new_block = "HTML = r'''" + new_html_content + "'''"
new_content = content[:start] + new_block + content[end:]

# Update window size: 800,740 -> 660,540
new_content = new_content.replace('ww,wh=800,740', 'ww,wh=660,540')
# Update min_size: 540,500 -> 500,420
new_content = new_content.replace('min_size=(540,500)', 'min_size=(500,420)')

# Write back
with open(target, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('SUCCESS: HTML block replaced, window size updated')
print('Old block length:', end - start)
print('New block length:', len(new_block))
