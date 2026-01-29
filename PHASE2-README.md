# 🚀 Church Automation - Phase 2 Containerization Complete

## What's New in Phase 2

This phase adds **full containerization support** using Docker/Podman, making it easy to deploy Church Automation on any Ubuntu server or Linux system.

### Key Additions

| Component | Purpose | Status |
|-----------|---------|--------|
| **Dockerfile** | Container image definition | ✅ Ready |
| **docker-compose.yml** | Container orchestration | ✅ Ready |
| **README-DEPLOYMENT.md** | Complete deployment guide | ✅ Ready |
| **Helper Scripts** | Setup and verification | ✅ Ready |

---

## Quick Deployment (Ubuntu Server)

### Prerequisites

```bash
# Install Docker/Podman
sudo apt-get update
sudo apt-get install docker.io docker-compose  # or podman + podman-compose
sudo usermod -aG docker $USER
```

### Deploy in 5 Steps

```bash
# 1. Create deployment directory
mkdir -p ~/church-automation-deployment/secrets
cd ~/church-automation-deployment

# 2. Clone or copy the repository
git clone https://github.com/FUMCWL/church-automation.git
cd church-automation

# 3. Prepare credentials (.env file):
# Create .env with Planning Center API credentials:
cat > .env << 'EOF'
PCO_CLIENT_ID=your_planning_center_client_id
PCO_SECRET=your_planning_center_secret
ANNOUNCEMENTS_WEBSITE_URL=https://www.fumcwl.org/weekly-events/
GCP_CREDENTIALS_FILENAME=gcp-credentials.json
EOF

# 4. Prepare config files (copy to secrets/):
# - slides_config.json (service type IDs and prayer lists)
# - gcp-credentials.json (optional - for AI summarization)

# 5. Build and start
docker-compose up -d
```

**Access the Web UI**: http://your-server-ip:8000

---

## Architecture

```
┌─────────────────────────────────────────────┐
│   Docker/Podman Container                   │
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────┐   │
│  │  FastAPI Web Server (Port 8000)     │   │
│  │  - Job Management Dashboard         │   │
│  │  - Real-time Status Updates         │   │
│  │  - File Download Endpoints          │   │
│  └─────────────────────────────────────┘   │
│           ↓        ↓         ↓              │
│  ┌─────────────────────────────────────┐   │
│  │  Background Job Runners             │   │
│  │  - Announcements (Web → PPTX)      │   │
│  │  - Service Slides (ProPresenter)    │   │
│  │  - Bulletins (PDF)                  │   │
│  └─────────────────────────────────────┘   │
│           ↓        ↓         ↓              │
│  ┌─────────────────────────────────────┐   │
│  │  External APIs                      │   │
│  │  - Announcements Website (web scrape)   │
│  │  - Planning Center (services)       │   │
│  │  - Google Vertex AI (summarization) │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         ↓         ↓          ↓
    ┌────────┬──────────┬──────────┐
    │Mounts  │Volumes   │Networks  │
    ├────────┼──────────┼──────────┤
    │Secrets │ Output   │Port 8000 │
    │(RO)    │Files     │          │
    └────────┴──────────┴──────────┘
```

---

## File Inventory

### Core Deployment Files

```
Dockerfile                 - Multi-stage container build (40 lines)
docker-compose.yml         - Service orchestration (27 lines)
.dockerignore              - Build optimization
README-DEPLOYMENT.md       - Complete deployment guide (500+ lines)
PHASE2-COMPLETION.md       - Implementation summary
```

### Helper Scripts

```
verify-deployment.sh       - Validate deployment setup (Unix)
verify-deployment.bat      - Validate deployment setup (Windows)
setup-deployment.sh        - Automated setup (Unix)
```

---

## Features

### Security ✅
- Environment variables in .env file (not in image)
- GCP credentials mounted read-only (optional)
- Environment variable isolation
- Non-root execution

### Reliability ✅
- Health check endpoint monitoring
- Automatic restart on failure
- Persistent output volumes
- Comprehensive error handling

### Performance ✅
- Slim base image (~150MB)
- Multi-stage build optimization
- Caching layer optimization
- No unnecessary dependencies

### Maintainability ✅
- Clear Dockerfile comments
- Standard Docker/Podman practices
- Easy dependency management
- Version-pinned packages

---

## Documentation

### For First-Time Deployment
→ Start with **README-DEPLOYMENT.md**

It includes:
- Prerequisites and installation
- Directory structure setup
- Credential file generation
- Step-by-step deployment
- Verification procedures
- Troubleshooting guide

### For Troubleshooting
→ See **README-DEPLOYMENT.md** → **Troubleshooting** section

Common issues covered:
- Port conflicts
- Missing credentials
- Import errors
- Slow performance

### For Advanced Configuration
→ See **README-DEPLOYMENT.md** → **Advanced Configuration** section

Topics covered:
- Custom ports
- Environment variables
- Additional storage
- Performance tuning

---

## Deployment Checklist

Before deploying to production:

- [ ] Read README-DEPLOYMENT.md completely
- [ ] Prepare credentials:
  - [ ] Gmail OAuth token
  - [ ] Planning Center API keys
  - [ ] GCP credentials (optional)
- [ ] Create deployment directory structure
- [ ] Build Docker image successfully
- [ ] Test health endpoint
- [ ] Generate sample files
- [ ] Verify file downloads work
- [ ] Set up log monitoring
- [ ] Plan backup strategy

---

## Service Architecture

### Container Services

| Service | Type | Port | Function |
|---------|------|------|----------|
| church-automation | FastAPI + Uvicorn | 8000 | Web UI + API |

### External Services

| Service | Type | Purpose |
|---------|------|---------|
| Gmail | REST API | Fetch announcements |
| Planning Center | REST API | Fetch service plans |
| Google Vertex AI | REST API | Summarize text |

### Storage

| Volume | Mount Point | Purpose | Access |
|--------|------------|---------|--------|
| secrets | /secrets | Credentials | Read-only |
| output | /app/output | Generated files | Read/Write |
| cache | /root/.cache | Python cache | Internal |

---

## Monitoring & Maintenance

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Last 50 lines
docker-compose logs --tail 50

# Search for errors
docker-compose logs | grep -i error
```

### Monitor Resources

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats church-automation

# Check disk space
df -h
```

### Maintenance Tasks

```bash
# Restart container
docker-compose restart

# Update container
docker-compose down
docker-compose up -d --build

# Backup files
tar -czf backup-$(date +%Y-%m-%d).tar.gz ./output/

# Cleanup old files
find ./output -type f -mtime +90 -delete
```

---

## Next Steps

### Phase 3: High Availability (Optional)

When you need redundancy and scaling:

1. **Kubernetes Setup**
   - Multi-node cluster
   - Auto-scaling
   - Load balancing

2. **Persistent Storage**
   - NFS or cloud storage
   - Backup automation

3. **Monitoring**
   - Prometheus + Grafana
   - ELK Stack for logs

4. **CI/CD**
   - Automated deployment
   - Version management

---

## Support & Issues

### Check Status

```bash
# Is container running?
docker-compose ps

# Are credentials accessible?
docker exec church-automation ls -la /secrets/

# Is web server responding?
curl http://localhost:8000/health
```

### Review Logs

```bash
# View container logs
docker-compose logs

# Check for specific errors
docker-compose logs | grep -i "error\|fail\|traceback"
```

### Verify Secrets

```bash
# Inside container
docker exec church-automation env | grep CHURCH_AUTOMATION

# Mount point
docker exec church-automation ls -la /secrets/
```

---

## Version Information

- **Phase**: 2 (Containerization)
- **Status**: Complete ✅
- **Docker Base**: Python 3.11-slim
- **Compose Version**: 3.8
- **Tested On**: Docker Desktop, Docker Community Edition

---

## Files Summary

```
PHASE 2 DELIVERABLES
├── Dockerfile (1.2 KB)
│   └── Multi-stage Python 3.11 container image
├── docker-compose.yml (611 B)
│   └── Service orchestration with volumes & health checks
├── .dockerignore (344 B)
│   └── Build optimization
├── README-DEPLOYMENT.md (9.4 KB)
│   └── Complete deployment & operations guide
├── PHASE2-COMPLETION.md (8.1 KB)
│   └── Implementation summary
├── verify-deployment.sh (2.0 KB)
│   └── Unix validation script
├── verify-deployment.bat (2.1 KB)
│   └── Windows validation script
└── setup-deployment.sh (1.6 KB)
    └── Automated setup script

TOTAL: 8 new files, ~25 KB documentation
```

---

**Phase 2 Status**: ✅ **COMPLETE AND READY FOR PRODUCTION**

You now have everything needed to deploy Church Automation on any Ubuntu server with Docker/Podman installed.

Start with: **README-DEPLOYMENT.md**
