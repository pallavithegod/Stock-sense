import sys
from pathlib import Path

def main():
    path = Path("d:/New3_Working_V3/app.py")
    if not path.exists():
        print(f"File {path} not found")
        return
    # read using latin-1 to preserve raw bytes
    with open(path, "r", encoding="latin-1") as f:
        lines = f.readlines()
    new_lines = []
    removed = 0
    for line in lines:
        # drop comment lines containing any non-ascii char
        if line.lstrip().startswith("#") and any(ord(ch) > 127 for ch in line):
            removed += 1
            continue
        new_lines.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Removed {removed} comment lines with non-ascii characters")

if __name__ == '__main__':
    main()
