import pathlib, json

path = pathlib.Path(r"d:\New3_Working_V3\app.py")
with open(path, 'rb') as f:
    lines = f.readlines()
line = lines[616]

# write raw bytes to file
with open(r"d:\New3_Working_V3\scripts\line_bytes.txt", 'wb') as f:
    f.write(line)

# hex representation
with open(r"d:\New3_Working_V3\scripts\line_hex.txt", 'w', encoding='utf-8') as f:
    f.write(' '.join(f"{b:02x}" for b in line))

# decode with latin1 and record ords and substring detection
s = line.decode('latin1', errors='ignore')
info = {
    'decoded': s,
    'has_substr': 'Ãƒ' in s,
    'ords': [ord(c) for c in s[:100]]
}
with open(r"d:\New3_Working_V3\scripts\line_info.json", 'w', encoding='utf-8') as f:
    json.dump(info, f)

# attempt filtering full file
text_latin = path.read_text(encoding='latin1')
lines_latin = text_latin.splitlines(keepends=True)
filtered = [l for l in lines_latin if 'Ãƒ' not in l]
path.write_text(''.join(filtered), encoding='latin1')

# record counts
counts = {'orig': len(lines_latin), 'filtered': len(filtered)}
with open(r"d:\New3_Working_V3\scripts\filter_counts.json", 'w') as f:
    json.dump(counts, f)

print('done writing logs to scripts folder')
