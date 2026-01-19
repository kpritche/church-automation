# AI Coding Agent Instructions for Church Automation

## Project Overview

Church Automation is a **Python monorepo** with independent installable packages that automate church media workflows:

1. **Announcements** (`packages/announcements/`) - Fetches weekly emails from Gmail, parses announcements, generates ProPresenter `.probundle` files with proper text formatting, QR codes, and images.
2. **Slides** (`packages/slides/`) - Connects to Planning Center Online (PCO) API, extracts service liturgy items, formats text into presentation slides, and generates ProPresenter `.pro` files via protobuf serialization.
3. **Bulletins** (`packages/bulletins/`) - Generates PDF bulletins from Planning Center service plans.
4. **Shared** (`packages/shared/`) - Common utilities for path management, configuration, and PCO credentials (required by all).

All workflows use **ProPresenter Protocol Buffers** - undocumented binary format that requires protobuf Python modules in `packages/slides/ProPresenter7_Proto/generated/`.

## Architecture & Data Flow

### Package Structure (Monorepo)

Each package is independently installable via `pip install -e ./packages/<name>` with its own `pyproject.toml`. Packages define console scripts for easy execution:

- `make-announcements` → `announcements_app.main_probundle:main`
- `make-slides` → `slides_app.make_pro:main`
- `make-bulletins` → `bulletins_app.make_bulletins:main`

**Critical:** Always install `packages/shared` first - all other packages depend on `church-automation-shared`.

### Key Modules

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| `announcements_app.main_probundle` | ProPresenter bundle generation (NEW workflow) | `make-announcements` or `python -m announcements_app.main_probundle` |
| `announcements_app.main` | Legacy PowerPoint workflow | `python -m announcements_app.main` (deprecated) |
| `announcements_app.probundle_generator` | Core ProPresenter bundle creation | `create_probundle(announcements, output_path)` |
| `slides_app.make_pro` | ProPresenter slide generation for services | `make-slides` or `python -m slides_app.make_pro` |
| `church_automation_shared.paths` | Centralized path management (critical!) | Imported everywhere; defines all output directories |
| `church_automation_shared.config` | PCO credentials and config loading | Loads `client_id` and `secret` for PCO API |

### Path Management Pattern

**ALL** path resolution flows through `church_automation_shared.paths`:

```python
# Never hardcode paths - always use church_automation_shared.paths
from church_automation_shared.paths import (
    ANNOUNCEMENTS_OUTPUT_DIR,
    SLIDES_TEMPLATES_DIR,
    SLIDES_OUTPUTS_DIR,
    SLIDES_DIR,  # Points to packages/slides/
    REPO_ROOT,   # Auto-calculated from package location
)

# User secrets live in ~/.church-automation/ (env var: CHURCH_AUTOMATION_SECRETS_DIR)
# Never store credentials in repo
```

**Import fallback pattern** (used when package not installed):

```python
try:
    from church_automation_shared.paths import ANNOUNCEMENTS_OUTPUT_DIR
except ModuleNotFoundError:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared.paths import ANNOUNCEMENTS_OUTPUT_DIR
```

### Configuration Pattern

Settings use a **fallback hierarchy**:

1. Environment variables (highest priority)
2. User config file (`config.py` in `announcements/` or repo root)
3. Defaults in `announcements_app/settings.py`

```python
# announcements_app/settings.py
_DEFAULTS = {
    "TITLE_MAX_CHARS": 120,
    "BRAND_COLOR_1": (22, 70, 62),
    "LOGO_PATH": ANNOUNCEMENTS_DIR / "logo.png",
}
# User can override by creating config.py with same attribute names
```

### Authentication & Secrets

- **Gmail**: OAuth2 via `google-auth-oauthlib` → token cached in `~/.church-automation/announcements_token.pickle`
- **PCO**: API credentials from `church_automation_shared.config` (exposed as `client_id` and `secret`)
- **Google Vertex AI**: GCP credentials JSON in `~/.church-automation/gcp-credentials.json` (filename configurable via `GCP_CREDENTIALS_FILENAME` env var)

## Critical Patterns

### 1. ProPresenter Protobuf Serialization

Both announcement and service slides generate `.pro` or `.probundle` files via protobuf:

- [announcements_app/probundle_generator.py](packages/announcements/announcements_app/probundle_generator.py) - Builds from scratch using protobuf message factories
- [slides_app/make_pro.py](packages/slides/slides_app/make_pro.py) - Clones templates and replaces text via protobuf `deepcopy()` and field mutation

**Key insight**: ProPresenter `.pro` files are serialized `Presentation` protobuf messages. Protobuf modules are in `packages/slides/ProPresenter7_Proto/generated/`:

```python
# In slides_app (ProPresenter7_Proto is packaged with it)
import ProPresenter7_Proto.generated.presentation_pb2 as rv_presentation

# In announcements_app (must add path manually)
_PROTO_PATH = Path(__file__).resolve().parents[3] / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
if str(_PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(_PROTO_PATH))

import presentation_pb2
import presentationSlide_pb2
import cue_pb2
import action_pb2
```

### 2. Text Formatting & RTF Generation

**Announcements** generate RTF from scratch in [probundle_generator.py](packages/announcements/announcements_app/probundle_generator.py):

```python
def generate_rtf_text(text: str, font_name: str = "SourceSansPro-Bold", 
                      font_size: int = 48, bold: bool = False, 
                      italic: bool = False, alignment: str = "left", 
                      color: tuple = None) -> bytes
```

**Slides** escape text for RTF injection in [make_pro.py](packages/slides/slides_app/make_pro.py):

```python
def _rtf_escape_text(value: str) -> str:
    # Handles backslashes, braces, newlines, Unicode
```

**Pattern**: Always use these functions when mutating slide text - don't build RTF manually.

### 3. Email Parsing

Announcements come from a specific Gmail inbox via a pattern-matched query:

```python
html_content = fetch_latest_announcement_html(
    service,
    query='from:First United Methodist Church subject:"The Latest FUMC News for You!"'
)
announcements = parse_announcements(html_content)  # Returns list of dicts
```

**Key fields**: `title`, `body`, `link`, `button_text`, `image_url` (optional)

### 4. Planning Center Online Integration

Service workflows query PCO for future Sunday items:

```python
from pypco.pco import PCO
from church_automation_shared import config
# Reads credentials from shared.config
pco = PCO(application_id=config.client_id, secret=config.secret)
```

**Workflow**:
1. Fetch service plan for next 7 days
2. Extract liturgy items (prayers, readings, etc.)
3. Parse text into properly-sized slide chunks via [content_parser.extract_items_from_pypco()](packages/slides/slides_app/content_parser.py)
4. Generate `.pro` files from templates using [slide_utils.slice_into_slides()](packages/slides/slides_app/slide_utils.py)

**Config location**: `packages/slides/slides_config.json` (template in `examples/slides_config.example.json`)

## Development Workflows

### Installation

```powershell
# Install packages in order (shared first)
pip install -e ./packages/shared
pip install -e ./packages/announcements
pip install -e ./packages/bulletins
pip install -e ./packages/slides
```

### Running Announcements Pipeline

```powershell
# Using console script (recommended)
make-announcements

# Or module syntax
cd packages/announcements
python -m announcements_app.main_probundle

# Output: packages/announcements/output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.probundle
```

### Running Service Slides Pipeline

```powershell
# Using console script (recommended)
make-slides

# Or module syntax
cd packages/slides
python -m slides_app.make_pro

# Output: packages/slides/output/YYYY-MM-DD/*-*.pro files
# Uploads to Planning Center if configured
```

### Unified Execution

```powershell
# From repo root - runs both pipelines sequentially
python run_all.py
```

## Important Conventions

- **Imports**: Always ensure `sys.path` adjustments happen BEFORE relative imports. See `run_all.py` for pattern.
- **Output directories**: Create via `os.makedirs(output_dir, exist_ok=True)` before writing.
- **Date handling**: Use ISO format (`YYYY-MM-DD`) for all output folder names and filenames.
- **Logging**: Use print statements (no logging framework configured). Include "✓" / "✗" prefixes for status.
- **Backwards compatibility**: Legacy aliases exist (e.g., `SERVICE_*` → `SLIDES_*` in `paths.py`). Use new names in new code.

## File Organization by Purpose

| Location | Purpose |
|----------|---------|
| `packages/announcements/announcements_app/` | Email → announcement slides (primary code) |
| `packages/slides/slides_app/` | Service liturgy → ProPresenter slides |
| `packages/bulletins/bulletins_app/` | Service plans → PDF bulletins |
| `packages/slides/templates/` | `.pro` template files (binary protobuf format) |
| `packages/shared/church_automation_shared/` | Cross-project utilities (paths, config) |
| `packages/slides/ProPresenter7_Proto/` | Protobuf definitions & generated Python modules |
| `examples/` | Configuration templates (`.env.example`, `slides_config.example.json`) |
| `assets/fonts/` | Shared font files |
| `deprecated/` | Legacy code (kept for reference, not used) |

## Common Tasks & Where to Find Them

| Task | File(s) |
|------|---------|
| Change email parsing logic | [announcements_app/html_parser.py](packages/announcements/announcements_app/html_parser.py) |
| Adjust slide text summarization | [announcements_app/summarize.py](packages/announcements/announcements_app/summarize.py) |
| Modify QR code generation | [probundle_generator.py](packages/announcements/announcements_app/probundle_generator.py#L300) |
| Change PCO query or item extraction | [slides_app/content_parser.py](packages/slides/slides_app/content_parser.py) |
| Add new font or asset | Update [shared/paths.py](packages/shared/church_automation_shared/paths.py) `FONT_SEARCH_PATHS` or `ASSETS_DIR` |
| Change output folder structure | Update [shared/paths.py](packages/shared/church_automation_shared/paths.py) output directory constants |
| Modify slide templates | Edit in ProPresenter GUI, save to [templates/](packages/slides/templates/) |

## Testing Notes

- No test runner configured - files like `test_line.py` are manual ad-hoc scripts
- Protobuf generation requires running `protoc` (in `packages/slides/protoc-*/bin/`); generated modules already committed
- Templates are binary `.pro` files that must be edited in ProPresenter GUI
- Test code execution directly with `python -m <module>` from package directory
