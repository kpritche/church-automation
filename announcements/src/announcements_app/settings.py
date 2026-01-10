"""Config defaults for announcements generation.

A user-specific config.py in the announcements folder (or repo root) can
override any of these attributes. This keeps secrets and per-machine tweaks
outside of version control while still providing sensible defaults.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

# Ensure repo root is importable so shared.* is available
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shared.paths import (
    ANNOUNCEMENTS_DIR,
    ANNOUNCEMENTS_GCP_CREDENTIALS_PATH,
    ASSETS_DIR,
)


_DEFAULTS = {
    "TITLE_MAX_CHARS": 120,
    "TITLE_WRAP_WIDTH": 32,
    "MAX_BODY_CHARS": 900,
    "BASE_FONT_SIZE": 28,
    "MIN_FONT_SIZE": 16,
    "BRAND_COLOR_1": (22, 70, 62),  # dark green
    "LOGO_PATH": ANNOUNCEMENTS_DIR / "logo.png",  # Use logo from announcements folder
    "GOOGLE_APPLICATION_CREDENTIALS": ANNOUNCEMENTS_GCP_CREDENTIALS_PATH,
}


def _load_user_config() -> Any:
    """Load an optional config.py (announcements-local first, then repo root)."""
    candidates = [ANNOUNCEMENTS_DIR / "config.py", _REPO_ROOT / "config.py"]
    for path in candidates:
        if path.exists():
            spec = importlib.util.spec_from_file_location("announcements_user_config", path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore[attr-defined]
                return module
    return None


_USER_CONFIG = _load_user_config()


def _get(name: str) -> Any:
    if name in os.environ:
        return os.environ[name]
    if _USER_CONFIG and hasattr(_USER_CONFIG, name):
        return getattr(_USER_CONFIG, name)
    return _DEFAULTS[name]


TITLE_MAX_CHARS = int(_get("TITLE_MAX_CHARS"))
TITLE_WRAP_WIDTH = int(_get("TITLE_WRAP_WIDTH"))
MAX_BODY_CHARS = int(_get("MAX_BODY_CHARS"))
BASE_FONT_SIZE = int(_get("BASE_FONT_SIZE"))
MIN_FONT_SIZE = int(_get("MIN_FONT_SIZE"))
BRAND_COLOR_1 = tuple(_get("BRAND_COLOR_1"))  # type: ignore[arg-type]
LOGO_PATH = Path(_get("LOGO_PATH"))
GOOGLE_APPLICATION_CREDENTIALS = Path(_get("GOOGLE_APPLICATION_CREDENTIALS"))

# Keep the environment variable in sync for Google clients
if GOOGLE_APPLICATION_CREDENTIALS:
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(GOOGLE_APPLICATION_CREDENTIALS))
