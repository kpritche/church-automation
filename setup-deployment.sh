#!/bin/bash
# Quick setup script for Church Automation deployment

set -e

DEPLOYMENT_DIR="${1:~\/church-automation-deployment}"

echo "🚀 Church Automation Deployment Setup"
echo "======================================"
echo ""
echo "Deployment directory: $DEPLOYMENT_DIR"
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p "$DEPLOYMENT_DIR/secrets"
mkdir -p "$DEPLOYMENT_DIR/output"
chmod 700 "$DEPLOYMENT_DIR/secrets"
echo "✓ Directories created"
echo ""

# Copy files
echo "📋 Copying configuration files..."
cp docker-compose.yml "$DEPLOYMENT_DIR/"
cp Dockerfile "$DEPLOYMENT_DIR/"
echo "✓ Files copied"
echo ""

# Instructions
cat << 'EOF'
✅ Setup complete!

Next steps:

1. Add credential files to the secrets directory:
   
   a) Gmail OAuth Token:
      cp ~/.church-automation/announcements_token.pickle DEPLOYMENT_DIR/secrets/
   
   b) Planning Center API Config:
      cat > DEPLOYMENT_DIR/secrets/slides_config.json << 'JSON'
{
  "pco_client_id": "your_pco_app_id",
  "pco_secret": "your_pco_secret"
}
JSON
   
   c) GCP Credentials (optional):
      cp ~/Downloads/gcp-key.json DEPLOYMENT_DIR/secrets/gcp-credentials.json

2. Verify secrets are set:
   ls -la DEPLOYMENT_DIR/secrets/

3. Build the Docker image:
   cd DEPLOYMENT_DIR
   docker build -t church-automation:latest .

4. Start the container:
   docker-compose up -d

5. Check health:
   curl http://localhost:8000/health

6. View logs:
   docker-compose logs -f

7. Access web UI:
   http://localhost:8000

For more information, see README-DEPLOYMENT.md
EOF

echo ""
echo "======================================"
