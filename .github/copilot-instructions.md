# AI Coding Agent Instructions for Church Automation

## Project Overview

Church Automation is a Python monorepo that automates two core workflows:

1. **Announcements** (`announcements/src/announcements_app/`) - Fetches weekly emails from Gmail, parses announcements, generates ProPresenter `.probundle` files (or legacy `.pptx` files) with proper text formatting, QR codes, and images.
2. **Slides** (`slides/src/service_app/`) - Connects to Planning Center Online (PCO) API, extracts service liturgy items, formats text into presentation slides, and generates ProPresenter `.pro` files via protobuf serialization.

Both workflows use **ProPresenter Protocol Buffers** - undocumented binary format that requires protobuf Python modules in `slides/ProPresenter7_Proto/generated/`.

## Architecture & Data Flow

### Key Modules

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| `announcements_app.main` | Legacy PowerPoint workflow | `python -m announcements_app.main` from `announcements/src` |
| `announcements_app.probundle_generator` | ProPresenter bundle generation | Used by `main_probundle.py` |
| `service_app.make_pro` | ProPresenter slide generation for services | `python -m service_app.make_pro` from `slides/src` |
| `shared.paths` | Centralized path management (critical!) | Imported everywhere; defines all output directories |

### Path Management Pattern

**ALL** path resolution flows through `shared/paths.py`:

```python
# Never hardcode paths - always use shared.paths
from shared.paths import ANNOUNCEMENTS_OUTPUT_DIR, SLIDES_TEMPLATES_DIR, SLIDES_OUTPUTS_DIR

# User secrets live in ~/.church-automation/ (env var: CHURCH_AUTOMATION_SECRETS_DIR)
# Never store credentials in repo
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
- **PCO**: API credentials from `shared/config.py` (already exposed but treat as sensitive)
- **Google Vertex AI**: GCP credentials JSON in `~/.church-automation/gmail-pptx-tool-1fa9ec3effd6.json`

## Critical Patterns

### 1. ProPresenter Protobuf Serialization

Both announcement and service slides generate `.pro` or `.probundle` files via protobuf:

- `probundle_generator.py` - Builds from scratch using protobuf message factories
- `make_pro.py` - Clones templates and replaces text via protobuf `deepcopy()` and field mutation

**Key insight**: ProPresenter `.pro` files are serialized `Presentation` protobuf messages. Always import from `ProPresenter7_Proto.generated`:

```python
from ProPresenter7_Proto.generated import presentation_pb2, cue_pb2, slide_pb2, graphicsData_pb2

# For announcements, path to proto modules is added in probundle_generator.py:
_PROTO_PATH = Path(__file__).resolve().parents[3] / "slides" / "ProPresenter7_Proto" / "generated"
sys.path.insert(0, str(_PROTO_PATH))
```

### 2. Text Formatting & RTF Generation

Both workflows handle RTF (Rich Text Format) encoding:

```python
# probundle_generator.py - generates RTF from scratch
def generate_rtf_text(text, font_name="SourceSansPro-Bold", font_size=48, 
                      bold=False, italic=False, alignment="left", color=None) -> bytes
```

```python
# make_pro.py - escapes text for RTF injection
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
# Reads credentials from shared.config
config_data = load_config(SLIDES_SLIDES_CONFIG)  # JSON with PCO API keys
pco = PCO(config_data["pco_user_id"], config_data["pco_key"])
```

**Workflow**:
1. Fetch service plan for next 7 days
2. Extract liturgy items (prayers, readings, etc.)
3. Parse text into properly-sized slide chunks via `content_parser.extract_items_from_pypco()`
4. Generate `.pro` files from templates using `slide_utils.slice_into_slides()`

## Development Workflows

### Running Announcements Pipeline

```bash
# New .probundle workflow (recommended)
cd announcements
python main_probundle.py
# Output: announcements/output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.probundle

# Legacy .pptx workflow
python main.py
# Output: announcements/output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.pptx
```

### Running Service Slides Pipeline

```bash
cd slides/src
python -m service_app.make_pro
# Output: slides/output/YYYY-MM-DD/*-*.pro files
# Uploads to Planning Center if configured
```

### Unified Execution

```bash
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
| `announcements/src/announcements_app/` | Email → announcement slides (primary code) |
| `announcements/*.py` | Legacy wrappers for backwards compatibility |
| `slides/src/service_app/` | Service liturgy → ProPresenter slides |
| `slides/templates/` | `.pro` template files (binary protobuf format) |
| `shared/` | Cross-project utilities (paths, config) |
| `slides/ProPresenter7_Proto/` | Protobuf definitions & generated Python modules |

## Common Tasks & Where to Find Them

| Task | File(s) |
|------|---------|
| Change email parsing logic | [announcements_app/html_parser.py](announcements_app/html_parser.py) |
| Adjust slide text summarization | [announcements_app/summarize.py](announcements_app/summarize.py) |
| Modify QR code generation | [probundle_generator.py](probundle_generator.py#L300) |
| Change PCO query or item extraction | [service_app/content_parser.py](../slides/src/service_app/content_parser.py) |
| Add new font or asset | Update [shared/paths.py](shared/paths.py) `FONT_SEARCH_PATHS` or `ASSETS_DIR` |
| Change output folder structure | Update [shared/paths.py](shared/paths.py) output directory constants |

## Testing Notes

- No test runner configured - files like `test_line.py` are manual ad-hoc scripts
- Protobuf generation requires running `protoc` (in `slides/protoc-*/bin/`); generated modules already committed
- Templates are binary `.pro` files that must be edited in ProPresenter GUI
