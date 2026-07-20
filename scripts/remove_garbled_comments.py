import pathlib

path = pathlib.Path(r"d:\New3_Working_V3\app.py")
# read raw bytes, decode latin1 to preserve bytes
text = path.read_text(encoding='latin1')
lines = text.splitlines(keepends=True)
# filter out any line whose latin1 decoding contains non-ascii after '# '
def is_comment_garbled(line):
    if not line.lstrip().startswith('#'):
        return False
    # check each character after '#' for ord>127
    for c in line:
        if ord(c) > 127:
            return True
    return False

filtered = [l for l in lines if not is_comment_garbled(l)]
path.write_text(''.join(filtered), encoding='latin1')
# also write counts to debug file
with open(path.with_suffix('.cleanlog'), 'w', encoding='utf-8') as f:
    f.write(f"orig={len(lines)}, filtered={len(filtered)}\n")
