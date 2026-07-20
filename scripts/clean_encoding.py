# -*- coding: utf-8 -*-
"""Repair and consolidate encoding utilities in utils/encoding.py.

This script is intended to be run in a shell to rewrite the module with a
single copy of the safe_text/UTF8Filter definitions and the mojibake-cleaning
logic.  It can be executed during development to keep the file tidy.
"""

import pathlib, re

ENCODING_PATH = pathlib.Path(r"d:\New3_Working_V3\utils\encoding.py")

# new unified definitions including mojibake filtering
NEW_SECTION = r"""# ---------------------------------------------------------------------------
# phase 5 safe string sanitization
# ---------------------------------------------------------------------------

# clear definition block with mojibake cleaning; docstrings omitted for brevity
_MOJIBAKE_RE = re.compile(r'ÃƒÆ’Ã‚Â¯Ãƒâ€šÃ‚Â¿Ãƒâ€šÃ‚Â½[Oo]?\\.?')

def remove_mojibake(s: str) -> str:
    return _MOJIBAKE_RE.sub("", s)

def safe_text(text: Any) -> str:
    s = str(text)
    s = remove_mojibake(s)
    return s.encode("utf-8", "ignore").decode("utf-8")

# ---------------------------------------------------------------------------
# logging helpers (phase 2 + filter for phase 5)
# ---------------------------------------------------------------------------

class UTF8Filter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        if record.msg is not None:
            record.msg = safe_text(record.msg)
        if record.args:
            try:
                record.args = tuple(safe_text(a) for a in record.args)
            except Exception:
                record.args = ()
        return True
"""


def rewrite():
    txt = ENCODING_PATH.read_text(encoding='utf-8')
    # remove everything from the first "phase 5 safe string sanitization" up to the bootstrap comment
    txt = re.sub(
        r"# ---------------------------------------------------------------------------\n# phase 5 safe string sanitization[\s\S]*?# run automatically if module is imported directly",
        NEW_SECTION + "\n\n# run automatically if module is imported directly",
        txt,
        count=1,
    )
    # drop any remaining secondary sections (duplicates)
    txt = re.sub(
        r"# ---------------------------------------------------------------------------\n# phase 5 safe string sanitization[\s\S]*?(?=# ---------------------------------------------------------------------------)",
        "# duplicate sanitization/filter definitions removed\n",
        txt,
    )

    # as a safety net, remove any lines after the special duplicate marker up
    # to the start of the configure_logging definition
    lines = txt.splitlines()
    filtered = []
    skip = False
    for line in lines:
        if line.strip().startswith('# duplicate sanitization/filter'):
            skip = True
            continue
        if skip and line.strip().startswith('def configure_logging'):
            skip = False
        if not skip:
            filtered.append(line)
    txt = "\n".join(filtered)

    ENCODING_PATH.write_text(txt, encoding='utf-8')

if __name__ == '__main__':
    rewrite()
    print('encoding.py cleaned successfully')
