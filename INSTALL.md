# Installation & Setup Guide

Complete step-by-step instructions for setting up the Church Automation Suite.

## Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) (recommended Python package installer)
- Git (for cloning the repository)

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/church-automation.git
cd church-automation
```

## Step 2: Install Python Packages

`uv` is a fast Python package installer and handles workspace dependencies automatically.

1. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Sync dependencies**:
   Run this from the root directory:
   ```bash
   uv sync --all-extras
   ```
   This will create a single `.venv` in the root and install all packages in editable mode.

## Step 3: Configure Environment Variables

### Create .env File

```bash
# Copy the example file
cp examples/.env.example .env

# Edit with your favorite editor
nano .env
# or
code .env
```

### Required Variables

Add your Planning Center credentials:

```bash
PCO_CLIENT_ID=your_planning_center_client_id_here
PCO_SECRET=your_planning_center_secret_here
```

**To get Planning Center credentials:**
1. Go to https://api.planningcenteronline.com/oauth/applications
2. Click "New Personal Access Token"
3. Give it a name (e.g., "Church Automation")
4. Copy the Application ID and Secret

### Optional Variables

```bash
# Customize Gmail query for your church
GMAIL_ANNOUNCEMENTS_QUERY=from:"communications@yourchurch.org" subject:"Weekly News"

# Override GCP credentials filename
GCP_CREDENTIALS_FILENAME=your-gcp-credentials.json

# Override secrets directory (default: ~/.church-automation)
CHURCH_AUTOMATION_SECRETS_DIR=/path/to/custom/secrets
```

## Step 4: Set Up Gmail API (For Announcements Only)

### Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Church Automation")
3. Enable the Gmail API:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Choose "Desktop application"
4. Download the JSON file
5. Rename it to `credentials.json`
6. Move it to `~/.church-automation/credentials.json`

### (Optional) Set Up Vertex AI for Summarization

1. In Google Cloud Console, enable "Vertex AI API"
2. Create a service account:
   - Navigate to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Grant "Vertex AI User" role
3. Create a key:
   - Click on your service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose JSON format
4. Download and save to `~/.church-automation/gcp-credentials.json`

## Step 5: Configure Planning Center Service Types

### Find Your Service Type IDs

1. Log into Planning Center Online
2. Go to Services
3. Click on a service type
4. Look at the URL: `https://services.planningcenteronline.com/service_types/[ID]`
5. Copy the ID number

### Create Configuration File

```bash
# Copy the example
cp examples/slides_config.example.json packages/slides/slides_config.json

# Edit it
nano packages/slides/slides_config.json
```

Add your service type IDs:

```json
{
  "service_type_ids": [1234567, 7654321]
}
```

## Step 6: Set Up QR Codes (For Bulletins Only)

Create the QR codes directory and add your images:

```bash
mkdir -p bulletins/qr_codes
```

Add these files (PNG or JPG):
- `giving.png` - QR code for online giving
- `bulletin.png` - QR code for digital bulletin
- `checkin.png` - QR code for check-in

## Step 7: Verify Installation

Test each package:

```bash
# Test announcements
python -m announcements_app.main_probundle

# Test bulletins  
python -m bulletins_app.make_bulletins

# Test slides
python -m slides_app.make_pro

# Or run everything
python run_all.py
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError`:
```bash
# Re-sync all packages
uv sync --all-extras
```

### Missing Credentials

If you see "Missing required environment variables":
1. Check that `.env` exists in the repository root
2. Verify `PCO_CLIENT_ID` and `PCO_SECRET` are set
3. Check for typos in variable names

### Gmail OAuth Issues

If Gmail authentication fails:
1. Verify `credentials.json` is in `~/.church-automation/`
2. Delete `announcements_token.pickle` and try again
3. Check that Gmail API is enabled in Google Cloud Console
4. Ensure OAuth consent screen is configured

### ProPresenter File Errors

If `.pro` file generation fails:
1. Check that templates exist in `packages/slides/templates/`
2. Verify protobuf is installed: `uv sync` (protobuf is a dependency)
3. Check that `ProPresenter7_Proto` directory exists in `packages/slides/`

### Path Issues

If output directories aren't found:
```bash
# Manually create them
mkdir -p packages/announcements/output
mkdir -p packages/bulletins/output
mkdir -p packages/slides/output
```

## Next Steps

- Review package-specific README files in `packages/*/README.md`
- Customize templates in `packages/slides/templates/`
- Adjust text limits and formatting in package settings
- Set up scheduled automation (cron jobs, Task Scheduler, etc.)

## Getting Help

- Check the main [README.md](README.md) for architecture overview
- Review `.github/copilot-instructions.md` for detailed technical documentation
- Look at example configurations in `examples/`
