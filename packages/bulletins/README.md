# Church Automation - Bulletin Generator

Generate PDF church bulletins from Planning Center service plans.

## Installation

It is recommended to use `uv` from the root directory to manage all packages:

```bash
uv sync
```

Alternatively, to install manually:

```bash
# From repository root
uv sync --all-extras
```

## Setup

### 1. Configure Environment

Add Planning Center credentials to your `.env` file:
```bash
PCO_CLIENT_ID=your_client_id
PCO_SECRET=your_secret
```

### 2. Add QR Codes

Place your church's QR code images in `bulletins/qr_codes/`:
- `giving.png` or `giving.jpg`
- `bulletin.png` or `bulletin.jpg`
- `checkin.png` or `checkin.jpg`

These will be printed three across on the last page of each bulletin.

## Usage

### Command Line

From the root directory using `uv`:

```bash
uv run make-bulletins
```

Or from within this directory if installed in your environment:

```bash
make-bulletins

# Or use module syntax
python -m bulletins_app.make_bulletins
```

### Output

Generated files are saved to `output/Bulletin-YYYY-MM-DD-ServiceName.pdf`

## Features

- **Planning Center Integration** - Fetches service plans for the next 7 days
- **Custom PDF Generation** - Uses ReportLab for precise layout control
- **Cover Images** - Automatically includes first attachment from "Bulletin Cover" item
- **Section Headers** - Planning Center header items become bulletin sections
- **HTML Formatting** - Preserves basic formatting from item descriptions
- **Brand Colors** - Enforces church color palette
- **Font Management** - Uses Source Sans Pro family with fallbacks
- **QR Codes** - Three QR codes on final page

## Configuration

### Layout Constants

Configured in `make_bulletins.py`:
- Page size: Letter (8.5" x 11")
- Margins: 30pt horizontal, 25pt vertical
- Font sizes: Title (14pt), Heading (12pt), Body (10pt)

### Brand Colors

Allowed colors (enforced in HTML parsing):
- `#000000` - Black
- `#16463e` - Dark teal
- `#51bf9b` - Light teal
- `#ff7f30` - Orange
- `#6fcfeb` - Cyan
- `#cda787` - Tan
- `#ffffff` - White

### Service Type Configuration

Edit `slides_config.json` to specify which Planning Center service types to generate bulletins for:
```json
{
  "service_type_ids": [1041663, 78127]
}
```

## Item Rules

- **Bulletin Cover** - First attachment becomes cover page image
- **Header Items** - Become section headers in the bulletin
- **Regular Items** - Title becomes sub-heading, description and HTML details printed below
- **Highlighted Text** - Ignored (not printed)

## Font Search Paths

The generator searches for fonts in:
1. `assets/fonts/`
2. `bulletins/fonts/`
3. `C:/Windows/Fonts/` (Windows)

Required fonts: Source Sans Pro (Regular, Bold, Italic, Bold Italic)

## Dependencies

- `pypco` - Planning Center Online API
- `reportlab` - PDF generation
- `pillow` - Image processing
- `PyPDF2` - PDF manipulation
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP client
- `church-automation-shared` - Common utilities
