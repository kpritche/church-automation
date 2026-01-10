# ProPresenter .probundle Generator

This tool generates ProPresenter `.probundle` files directly from email announcements, eliminating the need for intermediate PowerPoint files.

## Features

- ✅ Fetches announcements from Gmail
- ✅ Generates formatted ProPresenter slides with proper protobuf encoding
- ✅ Automatic QR code generation from links
- ✅ Downloads and embeds images
- ✅ Creates proper RTF formatted text
- ✅ Bundles everything into a single `.probundle` file

## Requirements

```bash
pip install qrcode pillow requests protobuf google-auth-oauthlib google-auth-httplib2 google-api-python-client beautifulsoup4
```

## Usage

### Generate .probundle file

```bash
cd announcements
python main_probundle.py
```

This will:
1. Fetch the latest announcements email from Gmail
2. Parse all announcements
3. Generate QR codes for links
4. Download announcement images
5. Create a `.probundle` file with all slides

Output location: `announcements/output/YYYY-MM-DD/weekly_announcements_YYYY-MM-DD.probundle`

### Generate .pptx file (legacy)

```bash
cd announcements
python main.py
```

## File Structure

Each announcement slide contains:

- **Title** (always present) - Large header text
- **Body** (always present) - Main announcement text
- **Logo** (always present) - Church logo
- **Image** (optional) - Main announcement image
- **QR Code** (optional) - Generated from announcement link
- **QR Text** (optional) - Button text or description

Elements are automatically removed if the data is not available (e.g., no image or QR code).

## Template

The generator uses the template from:
- `slides/templates/announcement_template.probundle`
- `slides/templates/announcement_template_extracted/announcement_template.pro`

To modify the template, edit the `.pro` file or create a new one in ProPresenter and place it in the templates directory.

## Architecture

### Module Structure

```
announcements/
├── main_probundle.py          # New .probundle entry point
├── main.py                     # Legacy .pptx entry point
├── src/
│   └── announcements_app/
│       ├── gmail_utils.py      # Gmail API authentication
│       ├── html_parser.py      # Parse announcement HTML
│       ├── summarize.py        # Text summarization
│       ├── ppt_generator.py    # Legacy PowerPoint generation
│       ├── probundle_generator.py  # NEW: ProPresenter generation
│       ├── main_probundle.py   # NEW: Entry point logic
│       └── settings.py         # Configuration
```

### Key Functions

**`probundle_generator.py`:**
- `create_probundle(announcements, output_path)` - Main function
- `create_announcement_slide(announcement, index, media_dir, template)` - Create single slide
- `generate_rtf_text(text, font, size, ...)` - Convert text to RTF
- `generate_qr_code(link, output_path)` - Generate QR code PNG
- `download_image(url, output_path)` - Download and save image
- `create_text_element(...)` - Create protobuf text element
- `create_media_element(...)` - Create protobuf media element

## Configuration

Edit `announcements/src/announcements_app/settings.py` or create `announcements/config.py`:

```python
# Logo path
LOGO_PATH = "/path/to/your/logo.png"

# Text limits
TITLE_MAX_CHARS = 120
MAX_BODY_CHARS = 900

# Font sizes
BASE_FONT_SIZE = 28
MIN_FONT_SIZE = 16

# Brand colors (RGB)
BRAND_COLOR_1 = (22, 70, 62)
```

## Troubleshooting

### Template not found
Ensure the template has been extracted:
```bash
cd slides
python decode_probundle.py templates/announcement_template.probundle
```

### Import errors
Make sure the ProPresenter7_Proto generated files exist:
```bash
ls slides/ProPresenter7_Proto/generated/
```

### Gmail authentication
Ensure credentials are set up:
- `~/.church-automation/gmail-pptx-tool-1fa9ec3effd6.json`
- `~/.church-automation/announcements_token.pickle`

## Differences from PowerPoint Generation

| Feature | .pptx (old) | .probundle (new) |
|---------|-------------|------------------|
| File format | PowerPoint | ProPresenter native |
| Template | Python code | Extracted .pro file |
| Text formatting | pptx library | RTF + protobuf |
| Media handling | Embedded | ZIP bundled |
| ProPresenter import | Manual import | Direct open |
| Slide transitions | None | Template preserved |
| Editing after | PowerPoint required | ProPresenter only |

## Future Enhancements

- [ ] Support for video elements
- [ ] Custom template selection
- [ ] Slide transitions configuration
- [ ] Advanced text styling (multiple fonts, colors)
- [ ] Background image support
- [ ] Animation effects
