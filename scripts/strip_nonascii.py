# remove lines from app.py containing any non-ASCII character (ord > 127)
path = r'd:\\New3_Working_V3\\app.py'
with open(path, 'r', encoding='latin-1') as f:
    lines = f.readlines()
new_lines = []
removed = 0
for line in lines:
    if any(ord(ch) > 127 for ch in line):
        removed += 1
        continue
    new_lines.append(line)
with open(path, 'w', encoding='latin-1') as f:
    f.writelines(new_lines)
print(f"removed {removed} lines containing non-ASCII characters")
