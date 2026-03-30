"""Configuration for Planning Center Online API access.

Load credentials from environment variables (.env file).
"""
import os
import sys
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Navigate to repo root: config.py -> church_automation_shared -> shared -> packages -> repo
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"Warning: .env file not found at {env_path}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your credentials.", file=sys.stderr)
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv", file=sys.stderr)

# Planning Center Online API credentials
# Must be set in .env file or as environment variables
client_id = os.getenv("PCO_CLIENT_ID")
secret = os.getenv("PCO_SECRET")

# Validate required credentials
if not client_id or not secret:
    missing = []
    if not client_id:
        missing.append("PCO_CLIENT_ID")
    if not secret:
        missing.append("PCO_SECRET")
    
    error_msg = (
        f"\n{'='*60}\n"
        f"ERROR: Missing required environment variables: {', '.join(missing)}\n\n"
        f"Please ensure these are set in your .env file:\n"
        f"  1. Copy .env.example to .env\n"
        f"  2. Fill in your Planning Center credentials\n"
        f"  3. Get credentials from: https://api.planningcenteronline.com/oauth/applications\n"
        f"{'='*60}\n"
    )
    print(error_msg, file=sys.stderr)
    # Don't exit - let the calling code handle the error gracefully
