import sys
path = r'd:\\New3_Working_V3\\app.py'
with open(path, 'rb') as f:
    data = f.read()
idx = data.find(b'# ')
print('first # at', idx)
# find all lines starting with '# ' and containing 0xc3 after
for i, line in enumerate(data.splitlines()):
    if line.startswith(b'# ') and b'\xc3' in line:
        print('line', i, 'bytes start', line[:60])
        break
