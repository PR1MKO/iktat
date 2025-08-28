# sitecustomize.py
"""
Force UTF-8 as the default encoding for pathlib.Path.read_text()
so tests that read template files without specifying an encoding
work reliably on Windows locales (e.g., cp1250).
Python automatically imports this module if it exists on sys.path.
"""

import pathlib

_original_read_text = pathlib.Path.read_text

def _read_text_utf8_default(self, *args, **kwargs):
    if "encoding" not in kwargs:
        kwargs["encoding"] = "utf-8"
    return _original_read_text(self, *args, **kwargs)

pathlib.Path.read_text = _read_text_utf8_default
