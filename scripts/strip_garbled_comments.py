# remove lines containing visible garbled sequences like 'Ãƒ' in app.py

path = r'd:\\New3_Working_V3\\app.py'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
new_lines = []
removed = 0
for line in lines:
    if 'Ãƒ' in line or 'Ã‚' in line or 'Ãƒ' in line:
        removed += 1
        continue
    new_lines.append(line)
with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print(f"stripped {removed} garbled comment lines")
