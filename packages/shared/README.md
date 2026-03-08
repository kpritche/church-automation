# Church Automation - Shared Utilities

Common utilities and configuration management for all church automation tools.

## Installation

```bash
# From repository root
uv sync
```

This package is installed automatically as part of the workspace.

## What's Included

### Configuration Management (`config.py`)

Loads Planning Center Online API credentials from environment variables:
- `PCO_CLIENT_ID` - Planning Center application ID
- `PCO_SECRET` - Planning Center secret or Personal Access Token

Automatically loads from `.env` file in repository root.

### Path Management (`paths.py`)

Centralized path definitions for all packages:
- Output directories
- Template locations
- Asset directories
- Font search paths
- Secrets directory (`~/.church-automation/` by default)

### Environment Variables

- `CHURCH_AUTOMATION_SECRETS_DIR` - Override default secrets location
- `GCP_CREDENTIALS_FILENAME` - Name of GCP credentials file in secrets dir

## Usage

```python
from church_automation_shared.paths import ANNOUNCEMENTS_OUTPUT_DIR
from church_automation_shared import config

print(config.client_id)  # PCO client ID
print(ANNOUNCEMENTS_OUTPUT_DIR)  # Path to announcements output
```

## Dependencies

- `python-dotenv` - Environment variable management
