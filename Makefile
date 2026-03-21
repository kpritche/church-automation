.PHONY: all announcements slides bulletins leader-guides bulletins-email bulletins-email-only web-ui install clean help test

# Default target - runs main workflows (announcements + slides)
all: announcements slides

# Run announcements generation workflow
announcements:
	@echo "Generating announcements..."
	uv run make-announcements

# Run service slides generation workflow
slides:
	@echo "Generating service slides..."
	uv run make-slides

# Run bulletin generation workflow
bulletins:
	@echo "Generating bulletins..."
	uv run make-bulletins

# Run leader guide generation workflow
leader-guides:
	@echo "Generating leader guides..."
	uv run make-service-leader-guide

# Generate bulletins, then email recent bulletin PDFs
bulletins-email:
	@echo "Generating and emailing bulletins..."
	./scripts/run_and_email_bulletins.sh

# Send email for recently generated bulletin PDFs only
bulletins-email-only:
	@echo "Emailing recently generated bulletins..."
	BULLETINS_EMAIL_SKIP_GENERATION=1 ./scripts/run_and_email_bulletins.sh

# Start web UI server
web-ui:
	@echo "Starting web UI server..."
	uv run serve-web-ui

# Install/sync all dependencies
install:
	@echo "Installing dependencies with uv..."
	uv sync --all-extras

# Clean build artifacts, cache, and generated files
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete"

# Run tests (if they exist)
test:
	@echo "Running tests..."
	uv run pytest

# Decode a ProPresenter file for inspection
# Usage: make decode FILE=path/to/file.pro
decode:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required"; \
		echo "Usage: make decode FILE=path/to/file.pro"; \
		exit 1; \
	fi
	@echo "Decoding $(FILE)..."
	uv run python decode_pro_file.py $(FILE)

# Test PCO API connectivity (useful for debugging)
test-api:
	@echo "Testing PCO API connectivity..."
	uv run python utils/test_pco_api.py

# Show available make targets
help:
	@echo "Church Automation - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Main Workflows:"
	@echo "  make all           - Run announcements + slides generation"
	@echo "  make announcements - Generate ProPresenter announcement slides"
	@echo "  make slides        - Generate ProPresenter service slides"
	@echo "  make bulletins     - Generate PDF bulletins"
	@echo "  make bulletins-email - Generate bulletins, then email PDFs"
	@echo "  make bulletins-email-only - Email recent bulletins only"
	@echo "  make web-ui        - Start the web UI server"
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install all dependencies with uv"
	@echo "  make clean         - Remove build artifacts and cache"
	@echo "  make test          - Run test suite"
	@echo "  make decode        - Decode .pro file (requires FILE=path)"
	@echo ""
	@echo "Examples:"
	@echo "  make all"
	@echo "  make announcements"
	@echo "  make decode FILE=output/service.pro"
