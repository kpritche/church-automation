import os
import json
from pathlib import Path

try:
    from church_automation_shared.paths import SLIDES_SLIDES_CONFIG
    from church_automation_shared import config
except ModuleNotFoundError:
    from pathlib import Path
    import sys
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared.paths import SLIDES_SLIDES_CONFIG
    from church_automation_shared import config
from pypco.pco import PCO

CONFIG_PATH = os.getenv("SLIDES_CONFIG", str(SLIDES_SLIDES_CONFIG))

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def attach_images_to_announcements(jpg_folder: str):
    # 1) Initialize PCO client
    pco = PCO(application_id=config.client_id, secret=config.secret)

    # 2) Find the plan for the upcoming Sunday (same logic as your main())
    from datetime import date, timedelta
    today = date.today()
    days_ahead = (6 - today.weekday()) % 7
    plan_date = (today + timedelta(days=days_ahead)).isoformat()

    cfg = load_config(CONFIG_PATH)
    service_ids = cfg.get("service_type_ids", [])  # add this to your config.py
    for stid in service_ids:
    # fetch plans
        plans = pco.iterate(f"/services/v2/service_types/{stid}/plans", filter="future")
        plan = None
        for candidate in plans:
            sort_date = candidate["data"]["attributes"].get("sort_date", "")
            if sort_date and sort_date[:10] == plan_date:
                plan = candidate
                break

        if plan is None:
            print(f"No plan scheduled for service type {stid} on {plan_date}; skipping image attachments.")
            continue

        plan_id = plan["data"]["id"]

        # 3) Fetch items & find the one titled "Announcements"
        items_resp = pco.get(
            f"/services/v2/service_types/{stid}/plans/{plan_id}/items"
        )
        ann_item = next(
            itm for itm in items_resp["data"]
            if itm["attributes"].get("title","") == "Announcements"
        )
        item_id = ann_item["id"]

        # 4) Loop through each JPG and attach it
        for fname in sorted(os.listdir(jpg_folder)):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
                print(f"Skipping non-image file: {fname}")
                continue
            path = os.path.join(jpg_folder, fname)

            # A) Upload file to get upload ID
            upload_resp = pco.upload(path)
            upload_id = upload_resp["data"][0]["id"]

            # B) Create attachment on the item
            attach_payload = {
                "data": {
                    "attributes": {
                        "file_upload_identifier": upload_id,
                        "filename": fname
                    }
                }
            }
            pco.post(
                f"/services/v2/service_types/{stid}"
                f"/plans/{plan_id}/items/{item_id}/attachments",
                payload=attach_payload
            )
            print(f"Attached {fname} to Announcements (item {item_id})")

if __name__ == "__main__":
    attach_images_to_announcements("C:\\Users\\KP\\Documents\\Github\\church\\announcements\\output\\2025-08-10")