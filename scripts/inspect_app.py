path = r"d:\New3_Working_V3\app.py"
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    for i, line in enumerate(f, 1):
        if i <= 630 and ('FEATURE 2' in line or 'Ã' in line):
            print(i, repr(line))
            print([ord(c) for c in line[:20]])
        if i > 640:
            break
