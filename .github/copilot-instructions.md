# AI Coding Agent Instructions for Church Automation

## Project Overview

Church Automation is a **Python monorepo** with independent installable packages that automate church media workflows:

1. **Announcements** (`packages/announcements/`) - Fetches weekly emails from Gmail, parses announcements, generates ProPresenter `.probundle` files with proper text formatting, QR codes, and images.
2. **Slides** (`packages/slides/`) - Connects to Planning Center Online (PCO) API, extracts service liturgy items, formats text into presentation slides, and generates ProPresenter `.pro` files via protobuf serialization.
3. **Bulletins** (`packages/bulletins/`) - Generates PDF bulletins from Planning Center service plans.
4. **Shared** (`packages/shared/`) - Common utilities for path management, configuration, and PCO credentials (required by all).

All workflows use **ProPresenter 7 Protocol Buffers** - an undocumented binary format requiring protobuf Python modules in `packages/slides/ProPresenter7_Proto/generated/`. These 45+ generated `*_pb2.py` modules are **already committed** - regeneration requires `protoc` binaries in `packages/slides/protoc-31.1-win64/`. **Only ProPresenter 7 is supported** - no backward or forward compatibility.

## Architecture & Data Flow

### Package Structure (Monorepo)

Each package is independently installable via `uv sync` with its own `pyproject.toml`. Packages define console scripts for easy execution:

- `make-announcements` → `announcements_app.main_probundle:main`
- `make-slides` → `slides_app.make_pro:main`
- `make-bulletins` → `bulletins_app.make_bulletins:main`

**Critical:** Use `uv sync --all-extras` from repository root to install all packages with their dependencies.

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

**Key insights**: 
- ProPresenter `.pro` files are serialized `Presentation` protobuf messages
- `.probundle` = ZIP archive containing: `.pro` file + `Media/Assets/` directory with images (QR codes, logos, photos)
- Templates live in `packages/announcements/templates/` as extracted directories (contains `.pro` + `.json` + `.txt` versions)
- Protobuf modules are in `packages/slides/ProPresenter7_Proto/generated/`

**ProPresenter Element Structure** (from template JSON):
- Presentation → cues[] → actions[] → slide → presentation → baseSlide → elements[]
- Each element has: `uuid`, `name`, `bounds` (position/size), `fill` (color/media), `text` (RTF data), `stroke`, `shadow`
- Media elements: reference files via `fill.media.url.local.path` (e.g., "Media/Assets/{UUID}.png")
- Text elements: store content in `text.rtfData` (base64-encoded RTF)

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

### 2. Template Loading & Element Manipulation

**Template Pattern**: Templates are **immutable references** - always load fresh for each generation:

```python
# Load template from directory (preferred - allows inspection)
template_dir = ANNOUNCEMENTS_DIR / "templates" / "announcement_template"
with open(template_dir / "announcement_template.pro", 'rb') as f:
    template_presentation = presentation_pb2.Presentation()
    template_presentation.ParseFromString(f.read())

# Or from .probundle (ZIP archive)
import zipfile
with zipfile.ZipFile(template_path, 'r') as z:
    pro_files = [f for f in z.namelist() if f.endswith('.pro')]
    with z.open(pro_files[0]) as f:
        template_presentation.ParseFromString(f.read())
```

**Finding Elements by Name** (use `element.name` field for reliable identification):

```python
for elem_wrapper in slide.base_slide.elements:
    elem = elem_wrapper.element
    if elem.name == "title_text":
        # Modify title element
    elif elem.name == "qr_code":
        # Update QR code media
    elif elem.name == "announcement_image":
        # Update image media
```

**Media Element Updates** (images, QR codes, logos):

```python
# Generate new UUID for media asset
media_uuid = str(uuid.uuid4()).upper()
elem.fill.media.uuid.string = media_uuid
elem.fill.media.url.local.path = f"Media/Assets/{media_uuid}.png"
elem.fill.media.image.drawing.natural_size.width = img.width
elem.fill.media.image.drawing.natural_size.height = img.height
```

### 3. Text Formatting & RTF Generation

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

**Pattern**: Always use these functions when mutating slide text - don't build RTF manually. RTF data is base64-encoded before assignment to `element.text.rtfData`.

### 4. Email Parsing

Announcements come from a specific Gmail inbox via a pattern-matched query:

```python
html_content = fetch_latest_announcement_html(
    service,
    query='from:First United Methodist Church subject:"The Latest FUMC News for You!"'
)
announcements = parse_announcements(html_content)  # Returns list of dicts
```

**Key fields**: `title`, `body`, `link`, `button_text`, `image_url` (optional)

### 5. Planning Center Online Integration

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

```bash
# From repository root - install all packages
uv sync --all-extras
```

This installs all packages in editable mode with a single `.venv` at the repository root.

### Debugging ProPresenter Files

Utility scripts in `utils/` for inspecting generated files. Use `uv run` or activate venv:

```bash
# Decode .pro file to JSON (primary debugging tool - kept in root)
uv run python decode_pro_file.py path/to/file.pro

# Analyze .probundle structure and media references
uv run python utils/analyze_bundle.py

# Compare two bundles
uv run python utils/compare_bundles.py bundle1.probundle bundle2.probundle

# Check template element structure
uv run python packages/announcements/inspect_template_elements.py
```

These scripts are **essential for development** - they reveal the actual protobuf structure, help debug media path issues, and verify element configurations.

### Running Announcements Pipeline

```bash
# Using console script (recommended)
uv run make-announcements

# Or module syntax
cd packages/announcements
uv run python -m announcements_app.main_probundle

# Output: packages/announcements/output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.probundle
```

### Running Service Slides Pipeline

```bash
# Using console script (recommended)
uv run make-slides

# Or module syntax
cd packages/slides
uv run python -m slides_app.make_pro

# Output: packages/slides/output/YYYY-MM-DD/*-*.pro files
# Uploads to Planning Center if configured
```

### Unified Execution

```bash
# From repo root - runs both pipelines sequentially
uv run python run_all.py
```

## Important Conventions

- **Imports**: Always ensure `sys.path` adjustments happen BEFORE relative imports. See `run_all.py` for pattern.
- **Output directories**: Create via `os.makedirs(output_dir, exist_ok=True)` before writing.
- **Date handling**: Use ISO format (`YYYY-MM-DD`) for all output folder names and filenames.
- **Logging**: Use print statements (no logging framework configured). Include "✓" / "✗" prefixes for status.
- **Backwards compatibility**: Legacy aliases exist (e.g., `SERVICE_*` → `SLIDES_*` in `paths.py`). Use new names in new code.
- **UUID generation**: Use `str(uuid.uuid4()).upper()` for all ProPresenter UUIDs (uppercase required).
- **Bundle creation**: `.probundle` files are **standard ZIP archives** (not 7z) with extension `.probundle`. Structure:
  ```
  weekly_announcements_YYYY-MM-DD.probundle/
  ├── weekly_announcements_YYYY-MM-DD.pro  (protobuf binary)
  └── Media/
      └── Assets/
          ├── {UUID}.png  (QR codes)
          ├── {UUID}.png  (announcement images)
          └── logo.png    (static assets)
  ```

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
- Protobuf generation requires running `protoc` (in `packages/slides/protoc-31.1-win64/bin/`); generated modules already committed
- **Template editing workflow** (requires ProPresenter 7 on Mac - manual process): 
  1. Edit `.pro` file in ProPresenter 7 GUI on Mac
  2. Save to `packages/announcements/templates/announcement_template/`
  3. Decode to JSON: `python decode_pro_file.py template.pro > template.json`
  4. Inspect structure to identify element names/UUIDs
  5. Update code to reference correct element names
- Test code execution directly with `python -m <module>` from package directory
- **Example workflow**: `examples/generate_probundle_example.py` demonstrates end-to-end bundle creation
