# Church Automation - Announcements Generator

Generate ProPresenter announcement slides from church website content.

## Installation

It is recommended to use `uv` from the root directory to manage all packages:

```bash
uv sync
```

Alternatively, to install manually:

```bash
# Install shared utilities first
pip install -e ../shared

# Install announcements package
pip install -e .
```

## Setup

### 1. Configure Environment

Add to your `.env` file:
```bash
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
```

### 2. GCP Service Account (Optional - for AI summarization)

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/)
2. Grant Vertex AI permissions
3. Download JSON key to `~/.church-automation/gcp-credentials.json`

## Usage

### Command Line

From the root directory using `uv`:

```bash
uv run make-announcements
```

Or from within this directory if installed in your environment:

```bash
make-announcements

# Or use module syntax
python -m announcements_app.main
```

### Output

Generated files are saved to `output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.probundle`

The `.probundle` files are automatically uploaded to Planning Center "Announcements" items if configured.

## Features

- **Website Fetching** - Automatically identifies and retrieves the most recent announcement page from the church website.
- **HTML Parsing** - Extracts titles, body text, links, and images from announcement HTML.
- **AI Summarization** - Condenses long text using Google Vertex AI.
- **QR Code Generation** - Creates QR codes for links and buttons.
- **ProPresenter Generation** - Builds `.probundle` files using protobuf serialization.
- **Planning Center Upload** - Automatically attaches generated files to service plans.

## Configuration

### Website URL

Customize the source URL in your `.env` file:

```bash
ANNOUNCEMENTS_WEBSITE_URL=https://yourchurch.org/announcements
```

### Text Limits

Configured in `announcements_app/settings.py`:
- `TITLE_MAX_CHARS` - Maximum characters for titles (default: 120)
- `MAX_BODY_CHARS` - Maximum characters for body text (default: 900)

## Dependencies

- `google-api-python-client` - Google API access
- `google-genai` - Vertex AI text generation
- `beautifulsoup4` - HTML parsing
- `qrcode[pil]` - QR code generation
- `pillow` - Image processing
- `protobuf` - ProPresenter file generation
- `python-pptx` - PowerPoint backup generation
- `py7zr` - Archive handling
- `church-automation-shared` - Common utilities
