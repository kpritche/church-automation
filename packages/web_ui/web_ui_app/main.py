"""FastAPI web application for church automation workflows"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import uuid
import os
import sys

# Ensure church_automation_shared is importable
try:
    from church_automation_shared.paths import (
        ANNOUNCEMENTS_OUTPUT_DIR,
        SLIDES_OUTPUTS_DIR,
        BULLETINS_OUTPUT_DIR,
        REPO_ROOT,
    )
except ModuleNotFoundError:
    # Fallback for development without installation
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared.paths import (
        ANNOUNCEMENTS_OUTPUT_DIR,
        SLIDES_OUTPUTS_DIR,
        BULLETINS_OUTPUT_DIR,
        REPO_ROOT,
    )
from web_ui_app.tasks import run_job_async, get_job_status, list_jobs, clear_completed_jobs

# Initialize FastAPI app
app = FastAPI(
    title="Church Automation Web UI",
    description="Web interface for managing church media automation workflows",
    version="0.1.0"
)

# Get template and static directories
TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent.parent / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# Pydantic models
class JobRequest(BaseModel):
    """Request to trigger a new job"""
    job_type: str  # "announcements", "slides", "bulletins"


class JobResponse(BaseModel):
    """Response containing job ID and initial status"""
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Detailed job status response"""
    job_id: str
    status: str
    type: str
    started_at: str
    completed_at: str | None = None
    error: str | None = None


# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve main UI page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/jobs", response_model=JobResponse)
async def trigger_job(request: JobRequest) -> JobResponse:
    """
    Trigger a background job to generate church media.
    
    Args:
        request: Job request with type specification
    
    Returns:
        JobResponse with job_id for status tracking
    
    Raises:
        HTTPException: If job_type is invalid
    """
    if request.job_type not in ["announcements", "slides", "bulletins"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job_type. Must be one of: announcements, slides, bulletins"
        )
    
    job_id = str(uuid.uuid4())
    run_job_async(job_id, request.job_type)
    
    print(f"✓ Job {job_id} queued: {request.job_type}")
    
    return JobResponse(job_id=job_id, status="queued")


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """
    Get status of a specific job.
    
    Args:
        job_id: UUID of the job
    
    Returns:
        Job status dictionary
    
    Raises:
        HTTPException: If job not found
    """
    status = get_job_status(job_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        **status
    }


@app.get("/api/jobs")
async def list_all_jobs():
    """
    List all jobs and their statuses.
    
    Returns:
        List of job status dictionaries
    """
    return {"jobs": list_jobs()}


@app.delete("/api/jobs")
async def clear_jobs():
    """
    Clear completed and failed jobs from memory.
    
    Returns:
        Count of cleared jobs
    """
    count = clear_completed_jobs()
    return {"cleared": count}


@app.get("/api/files/{job_type}")
async def list_files(job_type: str):
    """
    List available generated files for a job type.
    
    Args:
        job_type: Type of job (announcements, slides, bulletins)
    
    Returns:
        List of available files with dates
    
    Raises:
        HTTPException: If job_type is invalid
    """
    if job_type == "announcements":
        output_dir = ANNOUNCEMENTS_OUTPUT_DIR
        extension = ".pptx"  # Use PowerPoint format instead of probundle
        use_subdirs = True
    elif job_type == "slides":
        output_dir = SLIDES_OUTPUTS_DIR
        extension = ".pro"
        use_subdirs = True
    elif job_type == "bulletins":
        output_dir = BULLETINS_OUTPUT_DIR
        extension = ".pdf"
        use_subdirs = False  # Bulletins are flat
    else:
        raise HTTPException(status_code=400, detail="Invalid job_type")
    
    if not output_dir.exists():
        return {"files": []}
    
    files = []
    
    if use_subdirs:
        # Find all dated subdirectories (for announcements and slides)
        for date_dir in sorted(output_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            
            # Find files in this directory
            for file_path in date_dir.glob(f"*{extension}"):
                files.append({
                    "date": date_dir.name,
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
    else:
        # For bulletins, files are flat in the output directory
        for file_path in sorted(output_dir.glob(f"*{extension}"), key=lambda p: p.stat().st_mtime, reverse=True):
            if file_path.is_file():
                # Extract date from filename if possible (e.g., "Bulletin-2026-01-25-First-Up.pdf")
                filename = file_path.name
                date_str = None
                parts = filename.split("-")
                if len(parts) >= 3 and parts[0] == "Bulletin":
                    # Try to construct YYYY-MM-DD from Bulletin-YYYY-MM-DD format
                    try:
                        date_str = "-".join(parts[1:4])
                    except:
                        date_str = None
                
                files.append({
                    "date": date_str or "unknown",
                    "filename": filename,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
    
    return {"files": files}


@app.get("/api/files/{job_type}/{date}/{filename}")
async def download_file(job_type: str, date: str, filename: str):
    """
    Download a generated file.
    
    Args:
        job_type: Type of job (announcements, slides, bulletins)
        date: Date directory (YYYY-MM-DD format)
        filename: Name of the file
    
    Returns:
        File download response
    
    Raises:
        HTTPException: If file not found or job_type invalid
    """
    if job_type == "announcements":
        output_dir = ANNOUNCEMENTS_OUTPUT_DIR
        file_path = output_dir / date / filename
    elif job_type == "slides":
        output_dir = SLIDES_OUTPUTS_DIR
        file_path = output_dir / date / filename
    elif job_type == "bulletins":
        output_dir = BULLETINS_OUTPUT_DIR
        # Bulletins are flat in the output directory, not in subdirs
        file_path = output_dir / filename
    else:
        raise HTTPException(status_code=400, detail="Invalid job_type")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=filename
    )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors"""
    print(f"✗ Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    print("✓ Starting Church Automation Web UI on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
