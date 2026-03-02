# Church Automation - Announcements Generator

Generate ProPresenter announcement slides from your church's website.

## Installation

```bash
# Install shared utilities first
pip install -e ../shared

# Install announcements package
pip install -e .
```

## Setup

### 1. GCP Service Account (Optional - for AI summarization)

1. Create a service account in Google Cloud Console
2. Grant Vertex AI permissions
3. Download JSON key to `~/.church-automation/gcp-credentials.json`

### 2. Configure Environment

Add to your `.env` file:
```bash
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
```

## Usage

### Command Line

```bash
# Run the generator
make-announcements

# Or use module syntax
python -m announcements_app.main_probundle
```

### Output

Generated files are saved to `output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.probundle`

The `.probundle` files are automatically uploaded to Planning Center "Announcements" items if configured.

## Features

- **Website Scraping** - Automatically fetches the most recent announcement from your church website
- **HTML Parsing** - Extracts titles, body text, links, and images from announcement pages
- **AI Summarization** - Condenses long text using Google Vertex AI
- **QR Code Generation** - Creates QR codes for links and buttons
- **ProPresenter Generation** - Builds `.probundle` files using protobuf serialization
- **Planning Center Upload** - Automatically attaches generated files to service plans

## Configuration

### Website URL

Configure the URL of your church's weekly events page:

```bash
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
```

The tool will automatically find and fetch the most recent "View Weekly Events" link.

### Text Limits

Configured in `announcements_app/settings.py`:
- `TITLE_MAX_CHARS` - Maximum characters for titles (default: 120)
- `MAX_BODY_CHARS` - Maximum characters for body text (default: 900)

## Dependencies

- `requests` - HTTP requests for web scraping
- `google-genai` - Vertex AI text generation (optional)
- `beautifulsoup4` - HTML parsing
- `qrcode[pil]` - QR code generation
- `pillow` - Image processing
- `protobuf` - ProPresenter file generation
- `church-automation-shared` - Common utilities
