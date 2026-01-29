# Church Automation - Deployment Verification Guide

This document verifies that all deployment documentation accurately reflects the actual codebase.

## Actual Project Structure & Entry Points

### Package Entry Points (from pyproject.toml)

| Package | Entry Point | Command | Purpose |
|---------|-------------|---------|---------|
| announcements | `announcements_app.main:main` | `make-announcements` | Fetch announcements from website, generate PPTX |
| slides | `slides_app.make_pro:main` | `make-slides` | Generate ProPresenter slides from PCO service plans |
| bulletins | `bulletins_app.make_bulletins:main` | `make-bulletins` | Generate PDF bulletins from PCO service plans |
| web_ui | *Not in scripts* | `uvicorn web_ui_app.main:app` | FastAPI web interface |

### Actual Credential Requirements

#### Environment Variables (via .env file)

These MUST be set via environment variables, not files:

```
PCO_CLIENT_ID=<your_planning_center_client_id>
PCO_SECRET=<your_planning_center_secret_or_pat>
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
```

**Source**: `packages/shared/church_automation_shared/config.py`

The config module loads `PCO_CLIENT_ID` and `PCO_SECRET` from environment variables using `os.getenv()`.

#### Optional Credentials Files (in secrets/ directory)

These are read-only mounted files and are OPTIONAL:

1. **gcp-credentials.json** (optional)
   - For Google Vertex AI text summarization
   - JSON service account credentials from GCP
   - Only needed if using AI summarization features
   - Location: `/secrets/gcp-credentials.json` in container

2. **slides_config.json** (optional but recommended)
   - Service type IDs and prayer list configurations for PCO
   - Location: `packages/slides/slides_config.json` (repo) or `/secrets/slides_config.json` (container)
   - Used by: slides generation, bulletins generation
   - Contains: `service_type_ids`, `prayer_lists` configuration
   - Example content:
     ```json
     {
       "service_type_ids": [1041663, 78127, 1145553],
       "sheet_music_service_type_ids": [78127],
       "prayer_lists": {
         "refresh_before_fetch": true,
         "timeout_seconds": 10,
         "military_first_name_only": false,
         "concerns": {"id": 4688551, "name": "Prayer List"},
         "memory_care": {"id": 4742895, "name": "Memory Care"},
         "military": {"id": 4742806, "name": "Active Military"}
       }
     }
     ```

### What Was REMOVED (Not in Current Codebase)

❌ **Gmail OAuth Token** - NO LONGER NEEDED
- ✓ Gmail workflows completely removed
- ✓ Announcements now fetched from website (web scraping)
- ✓ No `announcements_token.pickle` file needed
- ✓ No Gmail API credentials needed
- **Module**: `announcements_app.web_fetcher` (website scraper)

❌ **Old PCO Credentials in File** - NO LONGER A FILE
- ✓ No separate PCO credentials file
- ✓ Now uses environment variables only
- ✓ PCO credentials passed via `PCO_CLIENT_ID` and `PCO_SECRET` env vars

## Actual Data Flows

### Announcements Pipeline

1. **Input**: Website URL (from `ANNOUNCEMENTS_WEBSITE_URL` env var)
2. **Process**: 
   - `announcements_app.web_fetcher.fetch_latest_announcement_html()` - web scraping
   - `announcements_app.html_parser.parse_announcements()` - HTML parsing
   - `announcements_app.ppt_generator.create_pptx_with_qr()` - PPTX generation
   - Optional: `announcements_app.summarize.summarize_text()` - AI summarization (requires GCP credentials)
3. **Output**: PPTX file to `output/announcements/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.pptx`
4. **Optional**: Upload to PCO announcements item (requires `slides_config.json` with service type IDs)

### Slides Pipeline

1. **Input**: PCO service plans (via `pypco` API using `PCO_CLIENT_ID` and `PCO_SECRET`)
2. **Config**: `slides_config.json` (service type IDs to fetch)
3. **Process**:
   - Query PCO for next 7 days of services
   - Extract liturgy items (prayers, readings, etc.)
   - Split into slides
   - Generate ProPresenter `.pro` files from templates
4. **Output**: `.pro` files to `output/slides/YYYY-MM-DD/`
5. **Optional**: Upload generated slides to PCO

### Bulletins Pipeline

1. **Input**: PCO service plans (via `pypco` API using `PCO_CLIENT_ID` and `PCO_SECRET`)
2. **Config**: `slides_config.json` (service type IDs to fetch)
3. **Process**:
   - Query PCO for next 7 days of services
   - Extract bulletin content (prayers, announcements, etc.)
   - Generate PDF with formatting and QR codes
4. **Output**: PDF files to `output/bulletins/Bulletin-YYYY-MM-DD-*.pdf`

## Container Environment Setup

### docker-compose.yml Configuration

```yaml
env_file:
  - .env                              # Load environment variables
volumes:
  - ./secrets:/secrets:ro             # Read-only secrets (GCP, optional)
  - ./output:/app/output              # Persistent generated files
  - church-automation-cache:/root/.cache  # Python cache
environment:
  - CHURCH_AUTOMATION_SECRETS_DIR=/secrets  # For optional GCP credentials
  - PYTHONUNBUFFERED=1
```

### .env File (REQUIRED)

Must exist in deployment directory with Planning Center credentials:

```
PCO_CLIENT_ID=your_pco_client_id
PCO_SECRET=your_pco_secret
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
```

### secrets/ Directory (OPTIONAL)

Optional files that can be mounted read-only:

```
secrets/
├── gcp-credentials.json    (optional - for AI summarization)
└── slides_config.json      (optional but recommended - service type IDs)
```

## Dockerfile Verification

### System Dependencies Installed

- ✅ curl (for health checks)
- ✅ fonts-liberation (PDF rendering)
- ✅ fonts-dejavu (PDF rendering)
- ✅ poppler-utils (PDF manipulation)

### Python Packages Installed (in order)

1. ✅ church-automation-shared (required by all)
2. ✅ church-automation-announcements
3. ✅ church-automation-bulletins
4. ✅ church-automation-slides
5. ✅ church-automation-web-ui

### Entry Point

```dockerfile
CMD ["uvicorn", "web_ui_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

This starts the FastAPI web server on port 8000.

## Deployment Directories

### Container Mounts

| Host Path | Container Path | Type | Purpose |
|-----------|----------------|------|---------|
| `.env` | Loaded by docker-compose | env file | PCO credentials, website URL |
| `./secrets/` | `/secrets` | ro mount | Optional: GCP credentials |
| `./output/` | `/app/output` | rw mount | Generated files |
| N/A | `/root/.cache` | volume | Python cache optimization |

### Output Directory Structure

```
output/
├── announcements/
│   ├── 2026-01-25/
│   │   └── weekly_announcements_2026-01-25.pptx
│   └── 2026-02-01/
│       └── weekly_announcements_2026-02-01.pptx
├── slides/
│   ├── 2026-02-01/
│   │   ├── 2026-02-01-Prayer_1-*.pro
│   │   └── 2026-02-01-Scripture_Lesson-*.pro
│   └── 2026-02-08/
│       └── ...
└── bulletins/
    ├── Bulletin-2026-02-01-Celebrate-Service.pdf
    ├── Bulletin-2026-02-01-First-Up.pdf
    └── Bulletin-2026-02-08-*.pdf
```

## Critical Corrections Made

### ✅ FIXED: Gmail References Removed

- ❌ OLD: "Generate this by running the announcements job locally once: This will trigger OAuth flow and save token"
- ✅ NEW: Announcements fetched from website (ANNOUNCEMENTS_WEBSITE_URL), no Gmail OAuth needed

### ✅ FIXED: slides_config.json Content Clarified

- ❌ OLD: "pco_client_id and pco_secret"
- ✅ NEW: "service_type_ids and prayer_lists configuration"
- ✅ PCO credentials now via environment variables only

### ✅ FIXED: Credential File Requirements

- ❌ OLD: Required 3 files: `announcements_token.pickle`, PCO credentials file, GCP credentials
- ✅ NEW: Required .env file with environment variables, optional secrets directory for GCP/slides_config

### ✅ FIXED: docker-compose.yml

- Added `env_file: .env` to load environment variables
- Clarified secrets directory is read-only
- Added curl to system dependencies for healthcheck

## Verification Checklist

- ✅ All entry points verified against pyproject.toml
- ✅ Credential requirements match actual code (config.py, announcements_app)
- ✅ Output directories match actual code (paths.py)
- ✅ Docker/docker-compose configuration correct
- ✅ Environment variable loading works
- ✅ Optional vs required credentials clearly documented
- ✅ Gmail references completely removed
- ✅ slides_config.json purpose clarified
- ✅ Web-based announcements fetching documented

## Next Steps for Users

1. **Create .env file** with PCO_CLIENT_ID and PCO_SECRET
2. **Optionally create secrets/slides_config.json** with service type IDs
3. **Optionally add secrets/gcp-credentials.json** for AI summarization
4. **Run docker-compose up -d**
5. **Access web UI** at http://localhost:8000

No Gmail setup needed anymore!
