import re

with open(r'c:\Users\DELL\Desktop\projects\student-management\templates\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check for Jinja start blocks: {% if, {% for, {% block, and ends: {% endif, {% endfor, {% endblock
ifs = len(re.findall(r'{%\s*if\b', text))
endifs = len(re.findall(r'{%\s*endif\b', text))
fors = len(re.findall(r'{%\s*for\b', text))
endfors = len(re.findall(r'{%\s*endfor\b', text))
blocks = len(re.findall(r'{%\s*block\b', text))
endblocks = len(re.findall(r'{%\s*endblock\b', text))

print(f"Ifs: {ifs}, EndIfs: {endifs}")
print(f"Fors: {fors}, EndFors: {endfors}")
print(f"Blocks: {blocks}, EndBlocks: {endblocks}")
