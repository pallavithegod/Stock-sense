import pathlib
import re

root = pathlib.Path(r"d:\New3_Working_V3")
changed_files = []
log_lines = []

for path in root.rglob("*.py"):
    # skip __pycache__ etc
    if "__pycache__" in path.parts:
        continue
    original_text = path.read_text(encoding="latin1")
    text = original_text

    # ensure utf-8 encoding header is present
    if not text.lstrip().startswith("# -*- coding: utf-8 -*-"):
        text = "# -*- coding: utf-8 -*-\n" + text

    # remove any non-ascii characters (phase 3 style sanitization)
    filtered = ''.join(c for c in text if ord(c) < 128)
    # optionally drop empty comment lines (# with only whitespace)
    lines = filtered.splitlines(keepends=True)
    cleaned_lines = []
    for line in lines:
        if line.strip() == "#" or re.match(r"^\s*#\s*$", line):
            # skip pure comment placeholder lines
            continue
        cleaned_lines.append(line)
    new_text = ''.join(cleaned_lines)
    if new_text != original_text:
        # write back using utf-8 to normalize encoding of file
        path.write_text(new_text, encoding="utf-8")
        changed_files.append(path)
        log_lines.append(f"modified {path}")

# write log
with open(root / "scripts" / "fix_encoding.log", "w", encoding="utf-8") as f:
    if log_lines:
        for l in log_lines:
            f.write(l + "\n")
    else:
        f.write("no changes\n")

if changed_files:
    print("modified files:")
    for p in changed_files:
        print(p)
else:
    print("no changes needed")
