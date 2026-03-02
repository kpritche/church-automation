# Multi-stage build for Church Automation Web UI
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    fonts-liberation \
    fonts-dejavu \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire monorepo
COPY packages/ ./packages/
COPY assets/ ./assets/

# Install packages in dependency order (shared first, then others)
RUN pip install --no-cache-dir -e ./packages/shared && \
    pip install --no-cache-dir -e ./packages/announcements && \
    pip install --no-cache-dir -e ./packages/bulletins && \
    pip install --no-cache-dir -e ./packages/slides && \
    pip install --no-cache-dir -e ./packages/web_ui

# Create secrets mount point & output directories
RUN mkdir -p /secrets /app/output

# Environment variables
ENV CHURCH_AUTOMATION_SECRETS_DIR=/secrets \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Run web UI by default
CMD ["uvicorn", "web_ui_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
