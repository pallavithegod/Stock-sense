import re

path = r"d:\New3_Working_V3\app.py"

# Read the file using latin-1 so we preserve byte values exactly
with open(path, 'r', encoding='latin-1', errors='ignore') as f:
    lines = f.readlines()

# Remove any line that contains the garbled character sequence
out_lines = []
for line in lines:
    if 'Ã' in line:
        # skip corrupted lines entirely
        continue
    out_lines.append(line)

# Ensure the normalize_prediction function has the correct docstring
final_lines = []
skipped_def = False
for line in out_lines:
    final_lines.append(line)
    if line.strip().startswith('def normalize_prediction') and not skipped_def:
        # insert a clean docstring immediately after the def
        final_lines.append('    """HARD CONTRACT - JS & WS rely on this\n')
        final_lines.append('    object being a dict of featureName -> value.  All other\n')
        final_lines.append('    code should use helpers in prediction_history."""\n')
        skipped_def = True

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

print("cleanup_app.py completed")
