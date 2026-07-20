# remove lines containing garbled sequences from app.py
import re
path = r'd:\\New3_Working_V3\\app.py'
with open(path, encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()
removed = []
with open(path, 'w', encoding='utf-8') as f:
    for line in lines:
        if 'Ãƒ' in line:
            removed.append(line.strip())
            continue
        f.write(line)
print(f'removed {len(removed)} lines containing garble')
if removed:
    print('sample removed lines:')
    for l in removed[:5]:
        print(l)
