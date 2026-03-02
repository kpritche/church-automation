"""Main entry point for generating .pptx announcements."""
from __future__ import annotations

import os
import sys
import json
from datetime import date, timedelta
from pathlib import Path

# Ensure packages are importable when running as script
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
_ANNOUNCEMENTS_PARENT = _REPO_ROOT / "packages" / "announcements"
if str(_SHARED_PARENT) not in sys.path:
    sys.path.insert(0, str(_SHARED_PARENT))
if str(_ANNOUNCEMENTS_PARENT) not in sys.path:
    sys.path.insert(0, str(_ANNOUNCEMENTS_PARENT))

from church_automation_shared.paths import ANNOUNCEMENTS_OUTPUT_DIR, SLIDES_SLIDES_CONFIG
from church_automation_shared import config
from announcements_app.web_fetcher import fetch_latest_announcement_html
from announcements_app.html_parser import parse_announcements
from announcements_app.ppt_generator import create_pptx_with_qr
from announcements_app.pro_generator import generate_pro_file
from announcements_app.summarize import summarize_text

try:
    from pypco.pco import PCO
    PYPCO_AVAILABLE = True
except ImportError:
    PYPCO_AVAILABLE = False


def get_next_sunday() -> date:
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday


def upload_to_planning_center(file_paths: list[Path], plan_date_str: str) -> bool:
    """Upload generated files to Planning Center announcements item.
    
    Args:
        file_paths: List of paths to files (e.g. .pptx, .probundle)
        plan_date_str: Date string in YYYY-MM-DD format
        
    Returns:
        True if at least one upload succeeded, False otherwise
    """
    if not PYPCO_AVAILABLE:
        print("   ⚠ pypco not available, skipping upload")
        return False
    
    try:
        # Initialize PCO client
        pco = PCO(application_id=config.client_id, secret=config.secret)
        
        # Load service type IDs from config
        if not SLIDES_SLIDES_CONFIG.exists():
            print(f"   ⚠ Config not found: {SLIDES_SLIDES_CONFIG}")
            return False
            
        with open(SLIDES_SLIDES_CONFIG, 'r') as f:
            cfg = json.load(f)
        
        service_type_ids = cfg.get('service_type_ids', [])
        if not service_type_ids:
            print("   ⚠ No service_type_ids in config")
            return False
        
        upload_count = 0
        for stid in service_type_ids:
            # Find the plan for the target date
            plans = pco.iterate(f"/services/v2/service_types/{stid}/plans", filter="future")
            plan = None
            plan_id = None
            
            for candidate in plans:
                sort_date = candidate["data"]["attributes"].get("sort_date", "")
                if sort_date and sort_date[:10] == plan_date_str:
                    plan = candidate
                    plan_id = plan["data"]["id"]
                    break
            
            if not plan_id:
                print(f"   ⚠ No plan found for service type {stid} on {plan_date_str}")
                continue
            
            # Find the Announcements item
            items_resp = pco.get(
                f"/services/v2/service_types/{stid}/plans/{plan_id}/items"
            )
            
            ann_item = None
            for itm in items_resp.get("data", []):
                if itm.get("attributes", {}).get("title", "") == "Announcements":
                    ann_item = itm
                    break
            
            if not ann_item:
                print(f"   ⚠ No 'Announcements' item found in service type {stid}")
                continue
            
            item_id = ann_item["id"]
            
            # Upload files to PCO
            print(f"   Uploading files to service type {stid}, plan {plan_id}...")
            
            for file_path in file_paths:
                print(f"     Uploading {file_path.name}...")
                upload_resp = pco.upload(str(file_path))
                upload_id = upload_resp["data"][0]["id"]
                
                # Attach to the Announcements item
                attach_payload = {
                    "data": {
                        "attributes": {
                            "file_upload_identifier": upload_id,
                            "filename": file_path.name
                        }
                    }
                }
                
                pco.post(
                    f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{item_id}/attachments",
                    payload=attach_payload
                )
                print(f"     ✓ {file_path.name} attached")
                
            upload_count += 1
        
        return upload_count > 0
        
    except Exception as e:
        print(f"   ✗ Upload failed: {e}")
        return False


def main() -> None:
    print("=" * 60)
    print("PPTX Announcements Generator")
    print("=" * 60)
    
    # Get website URL from environment or use default
    website_url = os.getenv(
        'ANNOUNCEMENTS_WEBSITE_URL',
        'https://www.fumcwl.org/weekly-events/'
    )
    
    # Fetch from website
    print("\n1. Fetching announcements from website...")
    html_content = fetch_latest_announcement_html(website_url)
    
    # Parse announcements
    print("\n2. Parsing announcements...")
    announcements = parse_announcements(html_content)
    print(f"   Found {len(announcements)} announcements")

    # Add summaries
    print("\n3. Generating summaries...")
    for idx, ann in enumerate(announcements, 1):
        print(f"   {idx}. {ann['title'][:50]}...")
        if "body" in ann:
            ann["summary"] = summarize_text(ann["body"], max_chars=180)
        else:
            ann["summary"] = "No summary available."

    # Create output directory
    date_str = get_next_sunday().strftime("%Y-%m-%d")
    output_dir = ANNOUNCEMENTS_OUTPUT_DIR / date_str
    output_path = output_dir / f"weekly_announcements_{date_str}.pptx"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n4. Creating ProPresenter file...")
    pro_output_path = output_dir / f"weekly_announcements_{date_str}.probundle"
    print(f"   Output: {pro_output_path}")
    generate_pro_file(announcements, str(pro_output_path), as_bundle=True)
    print(f"\n✓ ProPresenter bundle created: {pro_output_path}")
    
    print(f"\n5. Creating .pptx backup file...")
    print(f"   Output: {output_path}")
    create_pptx_with_qr(announcements, str(output_path), use_summary=True)
    print(f"\n✓ PPTX backup created: {output_path}")
    
    # Upload to Planning Center
    print(f"\n6. Uploading to Planning Center...")
    files_to_upload = [pro_output_path, output_path]
    upload_success = upload_to_planning_center(files_to_upload, date_str)
    
    print(f"\n{'=' * 60}")
    if upload_success:
        print(f"✓ Complete! Files saved and uploaded successfully")
    else:
        print(f"✓ Files saved (upload skipped or failed)")
    print(f"  {pro_output_path}")
    print(f"  {output_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
