"""Compatibility re-export for announcements_app.html_parser."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from announcements_app.html_parser import *  # type: ignore
