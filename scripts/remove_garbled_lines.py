# remove any line from app.py that contains non-ascii bytes
import sys
path = r'd:\\New3_Working_V3\\app.py'
with open(path, 'rb') as f:
    data = f.read()
    lines = data.splitlines(keepends=True)
new_lines = []
removed = 0
for line in lines:
    try:
        line.decode('ascii')
        new_lines.append(line)
    except UnicodeDecodeError:
        # line has non-ascii bytes, drop it
        removed += 1
with open(path, 'wb') as f:
    f.writelines(new_lines)
print(f"removed {removed} non-ascii lines")
