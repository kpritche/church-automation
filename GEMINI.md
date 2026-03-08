# Church Automation Suite - Gemini Context

This document provides essential context and instructions for AI agents working on the Church Automation Suite.

## Project Overview

The **Church Automation Suite** is a modular Python monorepo designed to automate workflows for church presentations, bulletins, and announcements. It integrates with **Planning Center Online (PCO)**, **Gmail**, and **Google Vertex AI** to streamline media production.

### Main Technologies
- **Language:** Python 3.9+
- **Dependency Management:** `uv` (with workspaces)
- **APIs:** Planning Center (pypco), Gmail API, Google GenAI (Vertex AI)
- **Output Formats:**
    - **ProPresenter 7:** Native `.pro` and `.probundle` files via Protocol Buffers.
    - **PDF:** Bulletins generated via `ReportLab`.
    - **PowerPoint:** Announcements optionally generated via `python-pptx`.
- **Web UI:** FastAPI with Jinja2 templates.

---

## Project Structure

The project is organized as a monorepo under the `packages/` directory:

- `packages/shared/`: Core infrastructure, path management (`paths.py`), and configuration loading.
- `packages/announcements/`: Fetches weekly announcements from Gmail, summarizes them using AI, and generates ProPresenter/PowerPoint files.
- `packages/slides/`: Converts Planning Center service plans into ProPresenter 7 presentations using Protobuf definitions located in `ProPresenter7_Proto/`.
- `packages/bulletins/`: Generates professionally formatted PDF bulletins from Planning Center data.
- `packages/web_ui/`: A FastAPI-based dashboard to trigger and monitor automation jobs.
- `assets/`: Shared resources like fonts (Source Sans Pro) and logos.
- `utils/`: Maintenance and debugging scripts for analyzing ProPresenter files and bundle structures.

---

## Building and Running

### Installation
The project uses `uv` for fast, reliable dependency management.
```bash
# Install all packages in the workspace
uv sync --all-extras
```

### Running Workflows
- **Unified Runner:** Execute the standard weekly workflow (announcements then slides).
  ```bash
  python run_all.py
  ```
- **Web UI:** Start the dashboard.
  ```bash
  python packages/web_ui/web_ui_app/main.py
  ```
- **Individual Commands:**
    - Announcements: `make-announcements`
    - Slides: `make-slides`
    - Bulletins: `python packages/bulletins/bulletins_app/make_bulletins.py`

---

## Development Conventions

### Coding Standards
- **Formatting:** Use `black`.
- **Type Checking:** Use `mypy`.
- **Testing:** Use `pytest`.
- **Imports:** Prefer absolute imports from the package name (e.g., `from church_automation_shared import paths`). Many scripts include fallbacks for local execution without installation.

### ProPresenter Protobuf
When modifying slide generation logic, refer to `packages/slides/ProPresenter7_Proto/`. This contains the generated Python code from ProPresenter 7's `.proto` definitions.

### Path Management
Always use `church_automation_shared.paths` for locating directories like `assets/`, `output/`, or `templates/` to ensure cross-platform and monorepo compatibility.

---

## Security & Credentials

- **Environment Variables:** Secrets are managed via a `.env` file at the root.
- **Sensitive Data:** Never commit `.env`, `.git`, or the `~/.church-automation/` directory.
- **OAuth:** Gmail OAuth tokens and Planning Center credentials should be stored in the configured secrets directory (defaults to `~/.church-automation/`).

---

## Key Files for Investigation
- `pyproject.toml`: Workspace configuration and dependencies.
- `run_all.py`: Orchestration logic.
- `packages/shared/church_automation_shared/paths.py`: Centralized path management.
- `packages/slides/slides_app/make_pro.py`: Core ProPresenter generation logic.
- `packages/announcements/announcements_app/main.py`: Announcement processing pipeline.
- `packages/bulletins/bulletins_app/make_bulletins.py`: PDF generation logic.
