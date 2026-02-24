# Church Automation Suite

The Church Automation Suite is a modular Python monorepo designed to automate workflows for church presentations, bulletins, and announcements. It integrates with Planning Center Online (PCO) and Gmail to streamline the creation of ProPresenter files and PDF bulletins.

## Project Overview

This suite consists of several independent but interoperable packages that automate common administrative and production tasks. By leveraging the Planning Center API and Google Workspace, it reduces manual data entry and ensures consistency across various media formats.

## Packages

### Shared Utilities (packages/shared)
The shared package provides the foundational infrastructure used by all other tools in the suite. It handles:
* Path management to ensure consistent file access across the monorepo.
* Configuration and environment variable loading.
* Planning Center API credential management.

### Announcements (packages/announcements)
The announcements package automates the transition from weekly announcement emails to ProPresenter slides. It performs the following functions:
* Fetches weekly announcement emails from Gmail using the Gmail API.
* Parses HTML content to extract individual announcement items.
* Utilizes Google Vertex AI to generate concise summaries for each announcement.
* Generates ProPresenter .probundle files containing formatted slides and QR codes for linked content.

### Slides (packages/slides)
The slides package converts Planning Center service plans into ProPresenter .pro files. Its core capabilities include:
* Fetching liturgy items, lyrics, and scripture references from Planning Center Online.
* Parsing content from various formats, including HTML and PDF attachments.
* Generating ProPresenter 7 files using Protocol Buffers.
* Supporting template-based slide generation to maintain visual consistency.

### Bulletins (packages/bulletins)
The bulletins package generates printable PDF bulletins based on Planning Center service data. Key features include:
* Extracting service orders and details from Planning Center plans.
* Creating professionally formatted PDFs using the ReportLab library.
* Embedding custom fonts and brand-specific styles.
* Integrating QR codes for giving, check-ins, and digital bulletin access.

## Getting Started

For detailed setup instructions, including prerequisite installation, API configuration, and environment setup, please refer to the [INSTALL.md](INSTALL.md) file.

## Technical Implementation

### ProPresenter Integration
This suite generates native ProPresenter 7 files by leveraging Google Protocol Buffers. The definitions and serialization logic are located within the `packages/slides/ProPresenter7_Proto/` directory. This allows for precise control over slide elements, including text, shapes, and media cues.

### Planning Center Online (PCO)
Integration with Planning Center is handled via the `pypco` library. The suite interacts with various PCO modules, primarily Services, to retrieve plan details, item notes, and attachments.

### AI Summarization
The announcements tool uses the Google GenAI (Vertex AI) SDK to summarize long-form email content into slide-ready text. This requires a Google Cloud Project with the Vertex AI API enabled.

## Directory Structure

* `assets/`: Shared resources such as fonts and logos.
* `examples/`: Configuration templates and example files.
* `packages/`: The core functional modules of the suite.
* `utils/`: Maintenance and debugging scripts for analyzing bundle structures and ProPresenter files.
* `run_all.py`: An orchestration script to execute the standard weekly workflow.

## Development

The project uses a monorepo structure where each package is defined with its own `pyproject.toml`. For development, it is recommended to install packages in editable mode as described in the installation guide.

### Code Quality
Maintain code quality by using the following tools from the root directory:
* Formatting: `black packages/`
* Type Checking: `mypy packages/`
* Testing: `pytest packages/`

## Security

* Do not commit `.env` files or any files containing API secrets.
* Gmail OAuth tokens and GCP service account keys should be stored in the configured secrets directory (defaulting to `~/.church-automation/`).
* Ensure that the `.gitignore` file is respected to prevent accidental disclosure of sensitive information.