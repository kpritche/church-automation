#!/usr/bin/env python3
"""
export_plans.py

Fetches Planning Center “plan” JSON (including items with arrangement & attachments)
for each service_type_id in slides_config.json and writes each to disk.
"""

import os
import sys
import json
from pathlib import Path
from datetime import date, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.paths import SLIDES_EXPORTED_PLANS_DIR, SLIDES_SLIDES_CONFIG
from shared import config          # contains client_id & secret (or PAT)
from pypco.pco import PCO
from deprecated.make_service_slides import load_config  # re-use your existing helpers

# Directory where JSON files will be written (unified under slides/output)
OUTPUT_DIR = os.getenv("EXPORT_DIR", str(SLIDES_EXPORTED_PLANS_DIR))


def ensure_output_dir(path: str):
    os.makedirs(path, exist_ok=True)


def export_plan_for_service(pco: PCO, service_type_id: str, plan_date: str):
    # 1) Get the service name for friendly filenames
    svc = pco.get(f"/services/v2/service_types/{service_type_id}")
    service_name = svc["data"]["attributes"]["name"].replace(" ", "")
    
    # 2) Find the plan matching our target date
    plans = pco.iterate(f"/services/v2/service_types/{service_type_id}/plans")
    plan_obj = next(
        (p for p in plans if p["data"]["attributes"]["sort_date"].startswith(plan_date)),
        None
    )
    if not plan_obj:
        print(f"No plan on {plan_date} for service_type_id={service_type_id}")
        return
    
    plan_id = plan_obj["data"]["id"]
    
    # 3) Fetch the full plan JSON, including items, arrangements & attachments
    plan_json = pco.get(
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}",
        include="items,items.arrangement,items.attachments"
    )

    items_json = pco.get(
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items",
        include="arrangement,attachments"
    
    )
    # 4) Write to disk
    plan_filename = f"{plan_date}–{service_name}–plan.json"
    items_filename = f"{plan_date}–{service_name}–items.json"
    plan_output_path = os.path.join(OUTPUT_DIR, plan_filename)
    items_output_path = os.path.join(OUTPUT_DIR, items_filename)
    with open(plan_output_path, "w", encoding="utf-8") as fp:
        json.dump(plan_json, fp, indent=2)
    print(f"Wrote plan JSON to {plan_output_path}")

    with open(items_output_path, "w", encoding="utf-8") as fp:
        json.dump(items_json, fp, indent=2)
    print(f"Wrote items JSON to {items_output_path}")


def main():
    # 0) Prep
    cfg = load_config(os.getenv("SLIDES_CONFIG", str(SLIDES_SLIDES_CONFIG)))
    service_ids = cfg.get("service_type_ids", [])
    if not service_ids:
        raise RuntimeError("No service_type_ids found in config")
    
    plan_date = "2026-01-04"
    print(f"Exporting plans for {plan_date}")
    
    ensure_output_dir(OUTPUT_DIR)
    
    # 1) Init PCO client
    pco = PCO(application_id=config.client_id, secret=config.secret)
    
    # 2) Loop through each service type
    for stid in service_ids:
        print(f"→ Service type {stid}")
        export_plan_for_service(pco, stid, plan_date)
    
    print("All done.")


if __name__ == "__main__":
    main()
