# -*- coding: utf-8 -*-
"""Utility: prepend UTF-8 encoding header to all Python modules."""
import pathlib
root = pathlib.Path(r"d:\New3_Working_V3")
for path in root.rglob("*.py"):
    if "__pycache__" in path.parts:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.lstrip().startswith('# -*- coding: utf-8 -*-'):
        path.write_text('# -*- coding: utf-8 -*-\n' + text, encoding="utf-8")
        print("patched", path)
