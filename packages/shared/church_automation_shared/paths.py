"""Centralized repository paths and sys.path helpers."""
from __future__ import annotations

from pathlib import Path
import os
import sys

# REPO_ROOT is now 3 levels up: church_automation_shared -> shared -> packages -> repo
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# User-specific secrets directory (not in repo)
_SECRETS_DIR = Path(os.getenv('CHURCH_AUTOMATION_SECRETS_DIR', 
                               str(Path.home() / '.church-automation')))

# Packages directory
PACKAGES_DIR = REPO_ROOT / "packages"

# Announcements
ANNOUNCEMENTS_DIR = PACKAGES_DIR / "announcements"
ANNOUNCEMENTS_OUTPUT_DIR = ANNOUNCEMENTS_DIR / "output"
ANNOUNCEMENTS_TOKEN_PATH = _SECRETS_DIR / "announcements_token.pickle"
ANNOUNCEMENTS_CREDENTIALS_PATH = _SECRETS_DIR / "credentials.json"
# GCP credentials for Vertex AI (configurable via env var)
_GCP_CREDS_FILENAME = os.getenv('GCP_CREDENTIALS_FILENAME', 'gcp-credentials.json')
ANNOUNCEMENTS_GCP_CREDENTIALS_PATH = _SECRETS_DIR / _GCP_CREDS_FILENAME

# Slides (formerly "service")
SLIDES_DIR = PACKAGES_DIR / "slides"
SLIDES_TEMPLATES_DIR = SLIDES_DIR / "templates"
SLIDES_SLIDES_CONFIG = SLIDES_DIR / "slides_config.json"
SLIDES_OUTPUTS_DIR = SLIDES_DIR / "output"
SLIDES_EXPORTED_PLANS_DIR = SLIDES_OUTPUTS_DIR / "exported_plans"

# Backwards compatibility aliases
SERVICE_DIR = SLIDES_DIR
SERVICE_TEMPLATES_DIR = SLIDES_TEMPLATES_DIR
SERVICE_SLIDES_CONFIG = SLIDES_SLIDES_CONFIG
SERVICE_OUTPUTS_DIR = SLIDES_OUTPUTS_DIR
SERVICE_EXPORTED_PLANS_DIR = SLIDES_EXPORTED_PLANS_DIR

# Bulletins
BULLETINS_DIR = PACKAGES_DIR / "bulletins"
BULLETINS_OUTPUT_DIR = BULLETINS_DIR / "output"
BULLETINS_QR_DIR = BULLETINS_DIR / "qr_codes"

# Leader Guide (service leader guide PDFs)
_LEADER_GUIDE_DEFAULT = Path(os.getenv(
    'LEADER_GUIDE_OUTPUT_DIR',
    r"C:\Users\Kory's PC\OneDrive - First United Methodist Church of West Lafayette\Scripts"
))
LEADER_GUIDE_OUTPUT_DIR = _LEADER_GUIDE_DEFAULT

# Assets
ASSETS_DIR = REPO_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

FONT_SEARCH_PATHS = (
    FONTS_DIR,
    SLIDES_DIR / "fonts",
    BULLETINS_DIR / "fonts",
    Path("C:/Windows/Fonts"),
)


def add_repo_root_to_sys_path() -> None:
    """Ensure the repository root is importable (for shared package access)."""
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def add_src_to_sys_path(*paths: Path) -> None:
    """Insert given src directories into sys.path if they exist."""
    for path in paths:
        if path and path.exists():
            s = str(path)
            if s not in sys.path:
                sys.path.insert(0, s)
