"""Background job execution system for church automation workflows"""

import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
import sys

# Global job status tracker (in-memory for Phase 1)
_JOB_STATUS: Dict[str, Dict] = {}


def run_job_async(job_id: str, job_type: str, params: dict = None) -> str:
    """
    Run long-running job in background thread.
    
    Args:
        job_id: Unique identifier for the job
        job_type: Type of job to run ("announcements", "slides", "bulletins")
        params: Optional parameters for the job
    
    Returns:
        job_id for status tracking
    """
    def execute():
        _JOB_STATUS[job_id] = {
            "status": "running",
            "type": job_type,
            "started_at": datetime.now().isoformat(),
            "output": [],
            "error": None,
            "completed_at": None
        }
        
        print(f"✓ Starting job {job_id}: {job_type}")
        
        try:
            if job_type == "announcements":
                from announcements_app.main import main as gen_announcements
                gen_announcements()
                _JOB_STATUS[job_id]["status"] = "completed"
                print(f"✓ Job {job_id} completed: announcements")
            
            elif job_type == "slides":
                from slides_app.make_pro import main as gen_slides
                gen_slides()
                _JOB_STATUS[job_id]["status"] = "completed"
                print(f"✓ Job {job_id} completed: slides")
            
            elif job_type == "bulletins":
                from bulletins_app.make_bulletins import main as gen_bulletins
                gen_bulletins()
                _JOB_STATUS[job_id]["status"] = "completed"
                print(f"✓ Job {job_id} completed: bulletins")
            
            else:
                raise ValueError(f"Unknown job type: {job_type}")
                
            _JOB_STATUS[job_id]["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            _JOB_STATUS[job_id]["status"] = "failed"
            _JOB_STATUS[job_id]["error"] = str(e)
            _JOB_STATUS[job_id]["traceback"] = traceback.format_exc()
            _JOB_STATUS[job_id]["completed_at"] = datetime.now().isoformat()
            print(f"✗ Job {job_id} failed: {e}")
            print(traceback.format_exc())
    
    thread = threading.Thread(target=execute, daemon=False)
    thread.start()
    
    return job_id


def get_job_status(job_id: str) -> Optional[Dict]:
    """
    Get status of a job by ID.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Job status dictionary or None if not found
    """
    return _JOB_STATUS.get(job_id)


def list_jobs() -> List[Dict]:
    """
    List all jobs with their current status.
    
    Returns:
        List of job status dictionaries
    """
    return [
        {"job_id": job_id, **status}
        for job_id, status in _JOB_STATUS.items()
    ]


def clear_completed_jobs() -> int:
    """
    Clear completed and failed jobs from memory.
    
    Returns:
        Number of jobs cleared
    """
    to_remove = [
        job_id for job_id, status in _JOB_STATUS.items()
        if status["status"] in ["completed", "failed"]
    ]
    
    for job_id in to_remove:
        del _JOB_STATUS[job_id]
    
    return len(to_remove)
