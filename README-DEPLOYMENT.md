# Church Automation - Containerized Deployment Guide

This guide provides instructions for deploying Church Automation using Podman/Docker containers.

## Overview

Church Automation is deployed as a containerized application with the following components:
- **Web UI**: FastAPI application for job management and file downloads
- **Job Runners**: Background threads executing announcement, slides, and bulletin generation
- **Output Storage**: Generated files are stored in mounted volumes
- **Secrets**: Credentials and configuration files mounted read-only

## Prerequisites

- **Podman** or **Docker** (this guide covers Podman, but Docker commands are identical)
- **4GB+ RAM** available for container
- **2GB+ disk space** for generated files

### Installation

**On Ubuntu/Debian:**
```bash
sudo apt-get install podman
```

**On macOS (with Homebrew):**
```bash
brew install podman
```

**On Windows:**
- Use Docker Desktop or Podman Desktop
- Or WSL2 with Podman installed

## Deployment Structure

Set up your deployment directory structure with the entire repository:

```
~/church-automation-deployment/
├── packages/                   (required - entire packages directory)
│   ├── shared/
│   ├── announcements/
│   ├── bulletins/
│   ├── slides/
│   └── web_ui/
├── assets/                     (required - fonts and assets)
│   └── fonts/
├── docker-compose.yml          (required - copy from repo)
├── Dockerfile                  (required - copy from repo)
├── .dockerignore               (optional - copy from repo)
├── .env                        (required - you create this)
├── secrets/                    (required - you create)
│   ├── gcp-credentials.json    (optional - for AI summarization)
│   └── slides_config.json      (optional - service configuration)
└── output/                     (auto-created on first run)
    ├── announcements/
    ├── slides/
    └── bulletins/
```

### 🚀 Quick Setup with Script

Use the provided setup script to automatically copy all required files:

**On Linux/macOS:**
```bash
./setup-deployment-dir.sh ~/church-automation-deployment
```

**On Windows:**
```powershell
.\setup-deployment-dir.bat C:\church-automation-deployment
```

This script will:
1. ✅ Create the deployment directory
2. ✅ Copy packages/, assets/, and Docker files
3. ✅ Create secrets/ directory
4. ✅ Create template .env file
5. ✅ Display next steps

## Step 1: Prepare Environment Variables

Create a `.env` file in your deployment directory with your Planning Center API credentials:

```bash
cat > ~/church-automation-deployment/.env << 'EOF'
# Planning Center Online API Credentials
# Get these from: https://api.planningcenteronline.com/oauth/applications
PCO_CLIENT_ID=your_planning_center_client_id_here
PCO_SECRET=your_planning_center_secret_or_pat_here

# Announcements Website URL
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/

# GCP Credentials filename (optional - for AI text summarization)
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
EOF

chmod 600 ~/church-automation-deployment/.env
```

**To generate Planning Center credentials:**
1. Visit https://api.planningcenteronline.com/oauth/applications
2. Create new personal access token or OAuth application
3. Copy `client_id` and `secret` to `.env` file

## Step 2: Prepare Secrets Directory

Create the secrets directory for optional credential files:

```bash
mkdir -p ~/church-automation-deployment/secrets
chmod 700 ~/church-automation-deployment/secrets
```

### Optional Credential Files

#### GCP Credentials for AI Summarization (`gcp-credentials.json`)

Optional - only needed if you want AI-powered text summarization for announcements.

```bash
# Download from GCP Console:
# 1. Create GCP Project
# 2. Enable Vertex AI API
# 3. Create Service Account with Vertex AI User role
# 4. Download JSON key file

cp ~/Downloads/gcp-key.json ~/church-automation-deployment/secrets/gcp-credentials.json
chmod 600 ~/church-automation-deployment/secrets/gcp-credentials.json
```

If not using GCP, you can skip this file entirely.

#### Planning Center Service Configuration (`slides_config.json`)

Create configuration file with service type IDs and prayer list configurations:

```bash
cat > ~/church-automation-deployment/secrets/slides_config.json << 'EOF'
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

chmod 600 ~/church-automation-deployment/secrets/slides_config.json
```

**To find your service type IDs:**
1. Visit Planning Center online as an admin
2. Go to Services → Manage Service Types
3. Each service type has an ID number in the URL or admin interface
4. Use the same IDs in the configuration above

**Prayer lists:** Configure the prayer list IDs from your Planning Center instance. You can customize or remove lists as needed.

## Step 3: Copy Repository Files

The container build requires the entire repository structure, not just Docker files. The Dockerfile references `packages/` and `assets/` directories.

```bash
cd ~/church-automation-deployment

# Copy the ENTIRE repository to your deployment directory
cp -r /path/to/church-automation/* .

# This copies:
# - packages/       (all 4+ packages)
# - assets/         (fonts and other assets)
# - docker-compose.yml
# - Dockerfile
# - .dockerignore
# - and other repo files
```

**Alternative: Use Git Clone**

If you prefer a clean checkout:

```bash
cd ~/church-automation-deployment

# Clone the repo into current directory
git clone https://github.com/FUMCWL/church-automation.git .
```

**Verify your deployment directory contains:**

```
~/church-automation-deployment/
├── packages/          ← REQUIRED (all packages)
│   ├── shared/
│   ├── announcements/
│   ├── bulletins/
│   ├── slides/
│   └── web_ui/
├── assets/            ← REQUIRED (fonts, etc.)
│   └── fonts/
├── docker-compose.yml ← REQUIRED
├── Dockerfile         ← REQUIRED
├── .env               ← REQUIRED (you create this)
└── secrets/           ← REQUIRED (you create this)
    ├── slides_config.json (optional)
    └── gcp-credentials.json (optional)
```

If any of these directories are missing, the Docker build will fail with "no such file or directory" error.

## Step 4: Build Container Image

```bash
cd ~/church-automation-deployment

# Build the image
podman build -t church-automation:latest .

# Or with docker:
docker build -t church-automation:latest .
```

**Build output should show:**
```
Successfully built church-automation:latest
Successfully tagged church-automation:latest
```

## Step 5: Start the Container

### Using Podman Compose

```bash
cd ~/church-automation-deployment

# Start in foreground (for testing)
podman compose up

# Or start in background
podman compose up -d

# View logs
podman compose logs -f

# Stop container
podman compose down
```

### Using Docker Compose

```bash
# Same commands as above, just use 'docker compose' instead
docker compose up -d
docker compose logs -f
docker compose down
```

## Step 6: Verify Deployment

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","timestamp":"2026-01-28T..."}

# Check container status
podman compose ps
podman compose logs --tail 20
```

## Usage

### Access the Web UI

Open browser to: **http://localhost:8000**

You should see three job cards:
- 📢 Announcements
- 📖 Service Slides  
- 📄 Bulletins

### Generate Media

1. Click any job card's "Generate" button
2. Status updates in real-time (green spinner)
3. When complete, click "View Files" to download

### Monitor Logs

```bash
# Real-time logs
podman compose logs -f

# Last 50 lines
podman compose logs --tail 50

# Specific service
podman compose logs -f church-automation
```

### Access Generated Files

Files are stored in `./output/` with structure:

```
output/
├── announcements/
│   ├── 2026-01-25/
│   │   └── weekly_announcements_2026-01-25.pptx
│   ├── 2026-02-01/
│   │   └── weekly_announcements_2026-02-01.pptx
│   └── ...
├── slides/
│   ├── 2026-02-01/
│   │   ├── 2026-02-01-Centering_Words-*.pro
│   │   ├── 2026-02-01-Song-*.pro
│   │   └── ...
│   └── ...
└── bulletins/
    ├── Bulletin-2026-02-01-Celebrate-Service.pdf
    ├── Bulletin-2026-02-01-First-Up.pdf
    └── ...
```

You can download files from the web UI or copy directly:

```bash
# Copy generated files to local machine
cp ~/church-automation-deployment/output/announcements/2026-02-01/*.pptx ~/Downloads/
```

## Troubleshooting

### Docker build fails: "no such file or directory" for packages/ or assets/

```
Error: executing ... docker-compose.exe up -d: exit status 1
COPY packages/ ./packages/: stat: "/packages": no such file or directory
```

**Cause**: You didn't copy the required `packages/` and `assets/` directories to your deployment directory.

**Solution**: 

```bash
# Make sure your deployment directory contains the ENTIRE repository
cd ~/church-automation-deployment

# Verify these directories exist:
ls -la packages/
ls -la assets/

# If missing, copy from the repo:
cp -r /path/to/church-automation/packages ./
cp -r /path/to/church-automation/assets ./

# Then rebuild:
docker compose build --no-cache
docker compose up -d
```

**Remember**: Docker builds in isolation and needs ALL referenced files in the build context. You can't use symlinks for `packages/` and `assets/` - they must be real directories.

```bash
# Check for errors
podman compose logs

# Common issues:
# 1. Port 8000 already in use
#    → Kill existing process or change port in docker compose.yml
# 2. Secrets files missing
#    → Verify all files exist in ./secrets/
# 3. Out of disk space
#    → Check: df -h
```

### Job fails with import error

```bash
# Rebuild container
podman compose down
podman image rm church-automation:latest
podman compose build --no-cache
podman compose up -d
```

### Credentials not found

```bash
# Verify environment variables are loaded
podman exec church-automation env | grep PCO_

# Check if slides_config.json exists
podman exec church-automation cat /secrets/slides_config.json

# Verify GCP credentials (if being used)
podman exec church-automation ls -la /secrets/gcp-credentials.json
```

### Jobs running very slowly

Monitor system resources:
```bash
# Check CPU/Memory usage
podman stats church-automation

# View logs for slowness indicators
podman compose logs -f | grep -i "processing\|generating"
```

## Maintenance

### Regular Cleanup

```bash
# Remove old generated files (older than 30 days)
find ./output -type f -mtime +30 -delete

# Prune old images/containers
podman system prune -a
```

### Update Church Automation

```bash
cd ~/church-automation-deployment

# Pull latest code from repo
git -C /path/to/church-automation pull origin main

# Rebuild container
podman compose build --no-cache

# Restart
podman compose up -d
```

### Backup Generated Files

```bash
# Backup announcements
tar -czf announcements-backup-$(date +%Y-%m-%d).tar.gz ./output/announcements/

# Backup all
tar -czf church-automation-backup-$(date +%Y-%m-%d).tar.gz ./output/
```

## Advanced Configuration

### Custom Port

Edit `docker compose.yml`:
```yaml
ports:
  - "8080:8000"  # Access at http://localhost:8080
```

### Custom Environment Variables

Add to `docker compose.yml`:
```yaml
environment:
  - CHURCH_AUTOMATION_SECRETS_DIR=/secrets
  - GCP_CREDENTIALS_FILENAME=gcp-credentials.json
  - PYTHONUNBUFFERED=1
```

### Mount Additional Storage

For high-volume output, mount external storage:
```yaml
volumes:
  - /mnt/external/announcements:/app/output/announcements
```

## Performance Tips

1. **Allocate adequate resources** - At least 4GB RAM
2. **Use SSD storage** - For `/output` volume
3. **Monitor logs** - Watch for performance warnings
4. **Schedule jobs** - Run during off-peak hours if possible
5. **Cleanup old files** - Archive and delete older than 90 days

## Support & Issues

- **Check logs**: `podman compose logs`
- **Verify credentials**: `podman exec church-automation ls -la /secrets/`
- **Test API**: `curl http://localhost:8000/health`

## Next Steps

- **Phase 3** (optional): Set up Kubernetes for high-availability deployment
- **Add monitoring**: Integrate with Prometheus/Grafana
- **Add authentication**: Implement API key or OAuth for web UI
- **Add scheduling**: Use cron or APScheduler for automated runs

---

**Last Updated**: January 28, 2026
**Church Automation Version**: 0.1.0
