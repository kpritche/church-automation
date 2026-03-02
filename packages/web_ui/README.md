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
pip install -e .
```

## Usage

Start the web server:

```bash
serve-web-ui
```

Or using uvicorn directly:

```bash
uvicorn web_ui_app.main:app --host 0.0.0.0 --port 8000
```

Access the UI at: http://localhost:8000

## Development

Install with dev dependencies:

```bash
pip install -e ".[dev]"
```
