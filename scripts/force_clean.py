import os
path = r"d:\New3_Working_V3\app.py"
with open(path, 'rb') as f:
    lines = f.readlines()

cleaned = []
for bline in lines:
    try:
        line = bline.decode('latin-1')
    except Exception:
        line = bline.decode('utf-8', errors='ignore')
    if 'Ã' in line:
        continue
    cleaned.append(line)

outpath = r"d:\New3_Working_V3\scripts\cleaned_app.py"
with open(outpath, 'w', encoding='utf-8') as out:
    out.writelines(cleaned)
print(f"wrote cleaned file to {outpath}")
