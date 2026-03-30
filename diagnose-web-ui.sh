#!/bin/bash
# Diagnostic script to troubleshoot web UI bulletins issue

echo "========================================="
echo "Web UI Bulletin Generation Diagnostics"
echo "========================================="
echo

echo "1. Checking Docker container status..."
sudo docker compose ps
echo

echo "2. Checking if web UI is responsive..."
curl -s http://localhost:8080/health | jq . || echo "Web UI not responding"
echo

echo "3. Checking mounted volumes..."
sudo docker compose exec church-automation ls -la /app/packages/bulletins/bulletins_app/ | grep make_bulletins.py
echo

echo "4. Checking output directory..."
sudo docker compose exec church-automation ls -la /app/packages/bulletins/output/ | tail -10
echo

echo "5. Checking config file..."
sudo docker compose exec church-automation cat /app/packages/slides/slides_config.json | jq .
echo

echo "6. Testing bulletins generation directly in container..."
echo "   (This will generate bulletins and show all debug output)"
echo
sudo docker compose exec church-automation python -c "
import os
os.environ['BULLETIN_DEBUG'] = '1'
from bulletins_app.make_bulletins import main
print('Starting bulletin generation...')
main()
print('Bulletin generation complete!')
"

echo
echo "7. Checking generated files..."
ls -lh packages/bulletins/output/Bulletin-2026-03-29-*.pdf 2>/dev/null | while read line; do
    file=$(echo "$line" | awk '{print $9}')
    if [ -n "$file" ]; then
        pages=$(sudo docker compose exec church-automation python -c "from PyPDF2 import PdfReader; print(len(PdfReader('$file').pages))" 2>/dev/null)
        echo "$line"
        echo "   └─ Pages: $pages"
    fi
done

echo
echo "========================================="
echo "Diagnostics complete!"
echo "========================================="
