# Church Automation Suite

A modular Python monorepo for automating church presentation and bulletin workflows using Planning Center Online and Gmail integration.

## 🎯 What This Does

This suite provides three independent tools that work together to automate common church media production tasks:

- **📢 Announcements** - Generate ProPresenter `.probundle` files from Gmail announcement emails
- **🖼️ Slides** - Generate ProPresenter `.pro` slides from Planning Center liturgy items
- **📄 Bulletins** - Generate PDF bulletins from Planning Center service plans

## 🏗️ Architecture

This is a **multi-package monorepo** where each tool can be installed and used independently:

```
church-automation/
├── packages/
│   ├── shared/                     # Common utilities (required by all)
│   ├── announcements/              # Gmail → ProPresenter announcements
│   ├── bulletins/                  # Planning Center → PDF bulletins
│   └── slides/                     # Planning Center → ProPresenter slides
├── examples/                       # Configuration templates
├── assets/                         # Shared fonts and resources
└── run_all.py                     # Unified runner for all tools
```

## 🚀 Quick Start

### 1. Install Packages

```bash
# Install shared utilities first (required by all tools)
pip install -e ./packages/shared

# Install the tools you need
pip install -e ./packages/announcements
pip install -e ./packages/bulletins
pip install -e ./packages/slides
```

### 2. Configure Credentials

```bash
# Copy environment template
cp examples/.env.example .env

# Edit .env and add your credentials:
# - PCO_CLIENT_ID and PCO_SECRET (get from Planning Center)
# - GMAIL_ANNOUNCEMENTS_QUERY (customize for your church)
```

### 3. Set Up Gmail OAuth (for announcements)

Place these files in `~/.church-automation/`:
- `credentials.json` - Gmail API OAuth credentials from Google Cloud Console
- `gcp-credentials.json` - GCP service account (optional, for AI summarization)

The first run will create `announcements_token.pickle` automatically.

### 4. Configure Service Types

```bash
# Copy and edit the slides config
cp examples/slides_config.example.json packages/slides/slides_config.json

# Add your Planning Center service type IDs
```

### 5. Run the Tools

```bash
# Run all tools sequentially
python run_all.py

# Or run individual tools
python -m announcements_app.main_probundle    # Or use: make-announcements
python -m bulletins_app.make_bulletins        # Or use: make-bulletins
python -m slides_app.make_pro                 # Or use: make-slides
```

## 📦 Package Details

### Shared Utilities (`church-automation-shared`)

Common functionality used by all tools:
- Path management and configuration
- Planning Center API credential handling
- Environment variable loading

**Dependencies:** `python-dotenv`

### Announcements (`church-automation-announcements`)

Fetches weekly emails from Gmail, parses announcements, generates summarized ProPresenter bundles with QR codes.

**Key Features:**
- Gmail API integration with OAuth2
- HTML email parsing
- AI-powered text summarization (Google Vertex AI)
- QR code generation
- ProPresenter protobuf serialization

**Dependencies:** `google-api-python-client`, `google-genai`, `beautifulsoup4`, `qrcode`, `pillow`, `protobuf`

**CLI Command:** `make-announcements`

### Bulletins (`church-automation-bulletins`)

Generates PDF church bulletins from Planning Center service plans.

**Key Features:**
- Planning Center API integration
- Custom PDF generation with ReportLab
- Font management (Source Sans Pro)
- Brand color enforcement
- QR code integration

**Dependencies:** `pypco`, `reportlab`, `pillow`, `PyPDF2`, `beautifulsoup4`

**CLI Command:** `make-bulletins`

### Slides (`church-automation-slides`)

Generates ProPresenter `.pro` slide files from Planning Center liturgy items.

**Key Features:**
- Planning Center API integration
- Protobuf-based `.pro` file generation
- Template cloning and text replacement
- Automatic file upload to Planning Center
- Scripture reference parsing

**Dependencies:** `pypco`, `protobuf`, `requests`

**Includes:** ProPresenter7 Protocol Buffer definitions

**CLI Command:** `make-slides`

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Required
PCO_CLIENT_ID=your_planning_center_client_id
PCO_SECRET=your_planning_center_secret

# Optional
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
GMAIL_ANNOUNCEMENTS_QUERY=from:"Your Church" subject:"Announcements"
CHURCH_AUTOMATION_SECRETS_DIR=/custom/secrets/path
```

### Planning Center Setup

1. Go to https://api.planningcenteronline.com/oauth/applications
2. Create a new Personal Access Token (PAT)
3. Add `PCO_CLIENT_ID` and `PCO_SECRET` to your `.env` file
4. Find your service type IDs in Planning Center (Services → Service Types → URL)
5. Add them to `packages/slides/slides_config.json`

### Gmail API Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download `credentials.json` to `~/.church-automation/`
5. Run announcements tool - it will open a browser for OAuth consent

## 📂 Directory Structure

```
packages/
├── shared/
│   └── church_automation_shared/
│       ├── __init__.py
│       ├── config.py              # API credentials
│       └── paths.py               # Path management
├── announcements/
│   ├── announcements_app/
│   │   ├── main_probundle.py     # Main entry point
│   │   ├── gmail_utils.py        # Gmail API
│   │   ├── html_parser.py        # Email parsing
│   │   ├── summarize.py          # AI summarization
│   │   └── probundle_generator.py # ProPresenter generation
│   ├── output/                    # Generated files
│   └── pyproject.toml
├── bulletins/
│   ├── bulletins_app/
│   │   └── make_bulletins.py     # Main entry point
│   ├── output/                    # Generated PDFs
│   └── pyproject.toml
└── slides/
    ├── slides_app/
    │   ├── make_pro.py            # Main entry point
    │   ├── content_parser.py      # PCO parsing
    │   └── slide_utils.py         # Slide formatting
    ├── ProPresenter7_Proto/       # Protobuf definitions
    ├── templates/                 # .pro templates
    ├── output/                    # Generated files
    └── pyproject.toml
```

## 🧪 Development

### Installing in Development Mode

```bash
# Install all packages in editable mode
pip install -e ./packages/shared
pip install -e ./packages/announcements
pip install -e ./packages/bulletins
pip install -e ./packages/slides

# With development dependencies
pip install -e "./packages/shared[dev]"
pip install -e "./packages/announcements[dev]"
```

### Running Tests

```bash
# Run tests for a specific package
cd packages/announcements
pytest tests/

# Or from repo root
pytest packages/announcements/tests/
```

### Code Quality

```bash
# Format code
black packages/

# Type checking
mypy packages/announcements/announcements_app/
```

## 🔒 Security Notes

- **Never commit `.env`** - it contains sensitive credentials
- All credentials are loaded from environment variables
- Gmail OAuth tokens are stored in `~/.church-automation/`
- Use `.gitignore` to protect sensitive files

## 📝 ProPresenter Protocol Buffers

The `.pro` files used by ProPresenter are Google Protocol Buffer files. Learn more about decoding and working with these undocumented files in `packages/slides/ProPresenter7_Proto/`, which is a fork of greyshirtguy's repository.

Example decode command:
```bash
protoc -I="packages/slides/ProPresenter7_Proto/Proto19beta" \
  --decode rv.data.Presentation propresenter.proto \
  < "output_file.pro" > decoded_output.txt
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues or questions:
- Check package-specific README files in `packages/*/`
- Review configuration examples in `examples/`
- See `.github/copilot-instructions.md` for detailed architecture notes
