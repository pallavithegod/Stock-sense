path = r"d:\New3_Working_V3\app.py"
with open(path, 'rb') as f:
    lines = f.readlines()

# inspect raw bytes of line 617
idx = 616  # 0-based index
if idx < len(lines):
    line = lines[idx]
    with open(r"d:\New3_Working_V3\scripts\byte_dump.txt", 'wb') as out:
        out.write(line)
    # also write hex bytes
    with open(r"d:\New3_Working_V3\scripts\hex_dump.txt", 'w', encoding='utf-8') as out:
        out.write('bytes: ' + ' '.join(hex(b) for b in line) + '\n')
    print('dumped line', idx+1)
else:
    print('line index out of range')
