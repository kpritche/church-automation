# Church Automation Web UI

Web interface for running church automation workflows.

## Features

- Generate announcement slides from your church website
- Generate service slides from Planning Center
- Generate PDF bulletins
- Download generated files
- Job status monitoring

## Installation

```bash
# From repository root
uv sync --all-extras
```

## Usage

Start the web server:

```bash
uv run serve-web-ui
```

Or using uvicorn directly:

```bash
uv run uvicorn web_ui_app.main:app --host 0.0.0.0 --port 8000
```

Access the UI at: http://localhost:8000
