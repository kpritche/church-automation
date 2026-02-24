# Gemini Context: Church Automation Suite

A modular Python monorepo for automating church presentation and bulletin workflows.

## 🏗️ Project Architecture

This is a **multi-package monorepo** using `setuptools` and `pyproject.toml` for each package. Packages are designed to be independent but share common utilities via the `shared` package.

### Core Packages (`/packages`)
- **`shared`**: Common utilities for path management (`paths.py`), configuration (`config.py`), and Planning Center API handling.
- **`announcements`**: Fetches weekly emails from Gmail, parses HTML, uses Google Vertex AI for summarization, and generates ProPresenter `.probundle` files with QR codes.
- **`slides`**: Fetches liturgy items from Planning Center Online (PCO), parses content (HTML/PDF), and generates ProPresenter `.pro` files using Protocol Buffers.
- **`bulletins`**: Generates PDF bulletins from PCO service plans using ReportLab.

## 🚀 Development Workflow

### Installation
Install all packages in editable mode to enable cross-package development:
```bash
pip install -e ./packages/shared
pip install -e ./packages/announcements
pip install -e ./packages/bulletins
pip install -e ./packages/slides
```

### Configuration
1. **Environment Variables**: Managed via a `.env` file in the root.
   - `PCO_CLIENT_ID`, `PCO_SECRET`: Planning Center API credentials.
   - `GMAIL_ANNOUNCEMENTS_QUERY`: Filter for Gmail fetching.
   - `CHURCH_AUTOMATION_SECRETS_DIR`: Path to secrets (defaults to `~/.church-automation`).
2. **Secrets Directory (`~/.church-automation`)**:
   - `credentials.json`: Gmail OAuth client secrets.
   - `gcp-credentials.json`: Google Cloud Service Account for Vertex AI.
   - `announcements_token.pickle`: Generated Gmail OAuth token.
3. **Slides Config**: `packages/slides/slides_config.json` defines target `service_type_ids`.

### Running Tools
- **Unified Runner**: `python run_all.py` (Runs announcements and slides).
- **Individual Commands**:
  - `make-announcements` (or `python -m announcements_app.main_probundle`)
  - `make-slides` (or `python -m slides_app.make_pro`)
  - `make-bulletins` (or `python -m bulletins_app.make_bulletins`)

## 🛠️ Technical Details

- **ProPresenter Integration**: Uses Google Protocol Buffers to generate `.pro` files. Definitions are located in `packages/slides/ProPresenter7_Proto/`.
- **PCO Integration**: Uses `pypco` for API interactions.
- **AI Summarization**: Uses `google-genai` (Vertex AI) to summarize announcement emails.
- **PDF Generation**: Uses `reportlab` with embedded fonts in `assets/fonts/`.

## 📏 Development Conventions

- **Path Management**: Always use `church_automation_shared.paths` for locating repo-relative files or output directories.
- **Imports**: Prefer absolute imports within packages. Use `add_repo_root_to_sys_path()` if executing scripts outside of the installed environment.
- **ProPresenter Templates**: Slide generation relies on template cloning (`white_template_mac.pro`, etc.). Do not modify these templates unless you intend to change the global slide style.
- **Security**: Never commit `.env`, `.pro`, `.probundle`, or `.pickle` files. Secrets must remain in the configured secrets directory.

## 📂 Key File Map
- `run_all.py`: Orchestrates the full weekly workflow.
- `packages/shared/church_automation_shared/paths.py`: Central authority for all filesystem paths.
- `packages/slides/slides_app/make_pro.py`: Complex logic for PCO-to-ProPresenter conversion.
- `packages/announcements/announcements_app/main_probundle.py`: Main logic for Gmail-to-ProPresenter conversion.
