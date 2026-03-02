#!/bin/bash
# Quick verification script for Church Automation deployment

set -e

echo "🔍 Church Automation - Deployment Verification"
echo "================================================"
echo ""

# Check Dockerfile exists
echo "✓ Checking Dockerfile..."
if [ -f "Dockerfile" ]; then
    echo "  ✓ Dockerfile found"
else
    echo "  ✗ Dockerfile not found"
    exit 1
fi

# Check docker-compose file exists
echo "✓ Checking docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    echo "  ✓ docker-compose.yml found"
else
    echo "  ✗ docker-compose.yml not found"
    exit 1
fi

# Check README
echo "✓ Checking README-DEPLOYMENT.md..."
if [ -f "README-DEPLOYMENT.md" ]; then
    echo "  ✓ README-DEPLOYMENT.md found"
else
    echo "  ✗ README-DEPLOYMENT.md not found"
    exit 1
fi

# Check all packages exist
echo "✓ Checking packages..."
for pkg in shared announcements bulletins slides web_ui; do
    if [ -d "packages/$pkg" ]; then
        echo "  ✓ packages/$pkg found"
    else
        echo "  ✗ packages/$pkg not found"
        exit 1
    fi
done

# Check assets
echo "✓ Checking assets..."
if [ -d "assets" ]; then
    echo "  ✓ assets directory found"
else
    echo "  ✗ assets directory not found"
    exit 1
fi

echo ""
echo "================================================"
echo "✅ All checks passed!"
echo ""
echo "Next steps:"
echo "1. Set up deployment directory:"
echo "   mkdir -p ~/church-automation-deployment/secrets"
echo ""
echo "2. Copy files:"
echo "   cp docker-compose.yml ~/church-automation-deployment/"
echo "   cp Dockerfile ~/church-automation-deployment/"
echo ""
echo "3. Add credentials to ~/church-automation-deployment/secrets/"
echo ""
echo "4. Build image:"
echo "   cd ~/church-automation-deployment"
echo "   docker build -t church-automation:latest ."
echo ""
echo "5. Start container:"
echo "   docker-compose up -d"
echo ""
echo "6. Access web UI:"
echo "   http://localhost:8000"
echo "================================================"
