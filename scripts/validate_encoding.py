# -*- coding: utf-8 -*-
"""Utility to verify that logs and source files are UTF-8 clean.

Run this periodically during health checks (Phase 8).
"""
from utils import encoding
import pathlib
import re

root = pathlib.Path(r"d:\New3_Working_V3")

print("Scanning Python files for missing header...")
missing = []
for path in root.rglob("*.py"):
    if "__pycache__" in path.parts:
        continue
    text = path.read_text(encoding='utf-8', errors='ignore')
    if not text.lstrip().startswith('# -*- coding: utf-8 -*-'):
        missing.append(path)
if missing:
    print("Missing header in:")
    for p in missing:
        print("   ", p)
else:
    print("All Python modules declare UTF-8 header.")

print("\nScanning logs for non-ASCII characters...")
logfile = root / 'logs' / 'nexus_ai.log'
if logfile.exists():
    bad_lines = []
    with logfile.open('r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, start=1):
            if re.search(r"[^\x00-\x7F]", line):
                bad_lines.append((i, line.strip()))
    if bad_lines:
        print("Found non-ASCII sequences in log:")
        for ln, text in bad_lines[:10]:
            print(f"{ln}: {text}")
    else:
        print("No non-ASCII characters detected in logs.")
else:
    print("Log file not found, skipping.")
