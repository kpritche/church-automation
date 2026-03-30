#!/usr/bin/env python3
"""Test to identify which part of bulletin generation is hanging.

This script isolates each step of the bulletin generation process to identify
where the hang occurs (PDF rendering, image processing, etc).

Run with: uv run python utils/test_bulletin_steps.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    from church_automation_shared import config
except ModuleNotFoundError:
    _REPO_ROOT = Path(__file__).resolve().parents[1]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared import config

from pypco.pco import PCO
import json


def test_step(name: str, func, timeout_sec: float = 10.0):
    """Run a test step and timeout if it takes too long."""
    print(f"\n[TEST] {name}")
    start = time.time()
    try:
        result = func()
        elapsed = time.time() - start
        print(f"  ✓ Completed in {elapsed:.2f}s")
        return result
    except KeyboardInterrupt:
        print(f"  ✗ Interrupted after {time.time() - start:.2f}s")
        raise
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ✗ Error after {elapsed:.2f}s: {type(e).__name__}: {e}")
        return None


def main():
    """Test bulletin generation steps."""
    print("=" * 60)
    print("Bulletin Generation Step Test")
    print("=" * 60)
    
    # Step 1: Load config
    def load_cfg():
        cfg_path = Path(__file__).parents[1] / "packages" / "slides" / "slides_config.json"
        with open(cfg_path) as f:
            return json.load(f)
    
    cfg = test_step("Load configuration", load_cfg)
    if not cfg:
        return
    
    # Step 2: Connect to PCO
    def connect_pco():
        return PCO(application_id=config.client_id, secret=config.secret)
    
    pco = test_step("Connect to PCO", connect_pco)
    if not pco:
        return
    
    # Step 3: Get service types
    def get_service_types():
        stypes = cfg.get("service_type_ids", [])
        if not stypes:
            raise ValueError("No service_type_ids in config")
        return stypes
    
    stypes = test_step("Get configured service types", get_service_types)
    if not stypes:
        return
    
    print(f"  Service types: {stypes}")
    
    # Step 4: Fetch service name
    def fetch_service_name():
        stid = stypes[0]
        resp = pco.get(f"/services/v2/service_types/{stid}")
        return resp["data"]["attributes"]["name"]
    
    service_name = test_step(f"Fetch service type name (#{stypes[0]})", fetch_service_name)
    print(f"  Service name: {service_name}")
    
    # Step 5: Find plans
    def find_plans():
        from datetime import date, timedelta
        stid = stypes[0]
        today = date.today()
        end = today + timedelta(days=7)
        start_date, end_date = today.isoformat(), end.isoformat()
        
        plans = []
        for plan_obj in pco.iterate(f"/services/v2/service_types/{stid}/plans", 
                                     filter="future"):
            plan_date = plan_obj["data"]["attributes"]["dates"]
            plan_data = plan_obj["data"]
            if start_date <= plan_date <= end_date:
                plans.append({
                    "plan": plan_data,
                    "plan_date": plan_date,
                })
        return plans
    
    plans = test_step("Fetch plans for service type", find_plans, timeout_sec=10.0)
    if not plans:
        print("  (No plans found in next 7 days)")
        return
    
    print(f"  Found {len(plans)} plan(s)")
    
    # Step 6: Get plan items
    def get_plan_items():
        stid = stypes[0]
        plan_id = plans[0]["plan"]["id"]
        resp = pco.get(
            f"/services/v2/service_types/{stid}/plans/{plan_id}/items",
            include="attachments"
        )
        return resp
    
    items_resp = test_step("Fetch plan items", get_plan_items)
    if not items_resp:
        return
    
    items = items_resp.get("data", [])
    print(f"  Found {len(items)} item(s)")
    
    # Step 7: Fetch team members
    def fetch_team():
        stid = stypes[0]
        plan_id = plans[0]["plan"]["id"]
        
        # Simplified version
        team_members = {}
        try:
            resp = pco.get(f"/services/v2/service_types/{stid}/plans/{plan_id}/team_members")
            for member in resp.get("data", []):
                position = member.get("attributes", {}).get("position_display_name", "Unknown")
                name = member.get("attributes", {}).get("person_name", "")
                if name:
                    if position not in team_members:
                        team_members[position] = []
                    team_members[position].append(name)
        except Exception as e:
            print(f"    (Warning: Could not fetch team: {e})")
        
        return team_members
    
    team = test_step("Fetch team members", fetch_team)
    if team:
        print(f"  Found {len(team)} positions")
    
    # Step 8: Load fonts (this might hang?)
    def load_fonts():
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from pathlib import Path as P
        
        font_paths = [
            P(__file__).parents[1] / "assets" / "fonts",
        ]
        
        try:
            for font_path in font_paths:
                for ttf in font_path.glob("*.ttf"):
                    try:
                        face_name = f"Font-{ttf.stem}"
                        pdfmetrics.registerFont(TTFont(face_name, str(ttf)))
                    except Exception as e:
                        pass
            return "Fonts loaded"
        except Exception as e:
            raise
    
    test_step("Load PDF fonts", load_fonts)
    
    # Step 9: Load QR codes
    def load_qr():
        from pathlib import Path as P
        qr_dir = P(__file__).parents[1] / "packages" / "bulletins" / "qr_codes"
        qr_files = list(qr_dir.glob("*.png")) if qr_dir.exists() else []
        return len(qr_files)
    
    num_qr = test_step("Load QR codes", load_qr)
    if num_qr:
        print(f"  Found {num_qr} QR code images")
    
    print("\n" + "=" * 60)
    print("All critical steps completed successfully!")
    print("The hang likely occurs during PDF rendering/item processing")
    print("=" * 60)


if __name__ == "__main__":
    main()
