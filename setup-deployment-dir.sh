#!/bin/bash
# Setup script to prepare deployment directory with all required files and structure

set -e

# Check if deployment directory argument provided
if [ -z "$1" ]; then
    echo "Usage: $0 <deployment-directory-path>"
    echo ""
    echo "Example:"
    echo "  $0 ~/church-automation-deployment"
    echo ""
    echo "This script will:"
    echo "  1. Create the deployment directory"
    echo "  2. Copy packages/, assets/, and Docker files from repo"
    echo "  3. Create secrets/ directory"
    echo "  4. Create a template .env file"
    echo ""
    exit 1
fi

DEPLOY_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Setting up Church Automation deployment directory..."
echo "   Target: $DEPLOY_DIR"
echo ""

# Create deployment directory
if [ -d "$DEPLOY_DIR" ]; then
    echo "⚠️  Directory already exists: $DEPLOY_DIR"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    mkdir -p "$DEPLOY_DIR"
    echo "✓ Created directory: $DEPLOY_DIR"
fi

# Copy required directories and files
echo ""
echo "Copying files from repository..."

# Copy packages directory
if [ -d "$SCRIPT_DIR/packages" ]; then
    cp -r "$SCRIPT_DIR/packages" "$DEPLOY_DIR/"
    echo "✓ Copied packages/"
else
    echo "✗ ERROR: packages/ directory not found in repo"
    exit 1
fi

# Copy assets directory
if [ -d "$SCRIPT_DIR/assets" ]; then
    cp -r "$SCRIPT_DIR/assets" "$DEPLOY_DIR/"
    echo "✓ Copied assets/"
else
    echo "✗ ERROR: assets/ directory not found in repo"
    exit 1
fi

# Copy Docker files
for file in Dockerfile docker-compose.yml .dockerignore; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        cp "$SCRIPT_DIR/$file" "$DEPLOY_DIR/"
        echo "✓ Copied $file"
    else
        echo "⚠️  Warning: $file not found"
    fi
done

# Create secrets directory
mkdir -p "$DEPLOY_DIR/secrets"
echo "✓ Created secrets/ directory"

# Create template .env file
echo ""
echo "Creating template .env file..."

cat > "$DEPLOY_DIR/.env.template" << 'EOF'
# Planning Center Online API Credentials
# Get these from: https://api.planningcenteronline.com/oauth/applications
PCO_CLIENT_ID=your_planning_center_client_id_here
PCO_SECRET=your_planning_center_secret_or_pat_here

# Announcements Website URL
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/

# GCP Credentials filename (optional - for AI text summarization)
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
EOF

echo "✓ Created .env.template"

# Check if .env already exists
if [ ! -f "$DEPLOY_DIR/.env" ]; then
    cp "$DEPLOY_DIR/.env.template" "$DEPLOY_DIR/.env"
    chmod 600 "$DEPLOY_DIR/.env"
    echo "✓ Created .env (from template)"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your Planning Center API credentials"
    echo "   File: $DEPLOY_DIR/.env"
else
    echo "✓ .env already exists (not overwritten)"
fi

# Create template slides_config.json
echo ""
echo "Creating template configuration files..."

cat > "$DEPLOY_DIR/secrets/slides_config.json.template" << 'EOF'
{
  "service_type_ids": [1041663, 78127, 1145553],
  "sheet_music_service_type_ids": [78127],
  "prayer_lists": {
    "refresh_before_fetch": true,
    "timeout_seconds": 10,
    "military_first_name_only": false,
    "concerns": {"id": 4688551, "name": "Prayer List"},
    "memory_care": {"id": 4742895, "name": "Memory Care"},
    "military": {"id": 4742806, "name": "Active Military"}
  }
}
EOF

echo "✓ Created slides_config.json.template"

# Directory structure summary
echo ""
echo "✅ Deployment directory ready!"
echo ""
echo "Directory structure:"
tree -L 2 "$DEPLOY_DIR" 2>/dev/null || find "$DEPLOY_DIR" -maxdepth 2 -type d | sort

echo ""
echo "📋 Next steps:"
echo ""
echo "1. Edit .env file with your Planning Center credentials:"
echo "   $DEPLOY_DIR/.env"
echo ""
echo "2. (Optional) Create slides_config.json with your service type IDs:"
echo "   cp $DEPLOY_DIR/secrets/slides_config.json.template $DEPLOY_DIR/secrets/slides_config.json"
echo "   # Edit with your actual service IDs"
echo ""
echo "3. (Optional) Add GCP credentials for AI summarization:"
echo "   cp ~/gcp-credentials.json $DEPLOY_DIR/secrets/"
echo ""
echo "4. Build the container:"
echo "   cd $DEPLOY_DIR"
echo "   docker-compose build"
echo ""
echo "5. Start the container:"
echo "   docker-compose up -d"
echo ""
echo "6. Access the web UI:"
echo "   http://localhost:8000"
echo ""
