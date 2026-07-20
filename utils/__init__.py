# -*- coding: utf-8 -*-
"""Utility package initialization.  

This module bootstraps UTF-8 handling as soon as any part of the package is
imported.  It also re-exports common helpers so callers can do
``from utils import safe_text`` etc.  
"""

# run bootstrap immediately when package is loaded
from .encoding import bootstrap_utf8, safe_text, configure_logging, UTF8Filter, ensure_json_utf8

bootstrap_utf8()

# let clients import utilities directly
__all__ = [
    "bootstrap_utf8",
    "safe_text",
    "configure_logging",
    "UTF8Filter",
    "ensure_json_utf8",
]
