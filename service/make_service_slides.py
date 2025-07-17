#!/usr/bin/env python3
"""
make_service_slides.py

Orchestrator: reads slides_config.json for service_type_ids,
computes the upcoming Sunday, fetches plans via the pypco PCO client,
parses content, slices into slides, and for each item with HTML:
  1) generates a PPTX per item
  2) uploads the PPTX file via pco.upload()
  3) creates a Media record linked to that upload
  4) associates the Media with the plan item

Configuration (client_id & secret) is loaded from config.py.
"""
import os
import json
from datetime import date, timedelta

import config
from pypco.pco import PCO
from content_parser import extract_items_from_pypco
from slide_utils import slice_into_slides
from ppt_generator_services import create_pptx_for_items

CONFIG_PATH = os.getenv("SLIDES_CONFIG", "slides_config.json")


def get_upcoming_sunday() -> str:
    today = date.today()
    days_ahead = (6 - today.weekday()) % 7
    return (today + timedelta(days=days_ahead)).isoformat()


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    service_ids = cfg.get("service_type_ids", [])
    if not service_ids:
        raise ValueError(f"No service_type_ids in config: {CONFIG_PATH}")

    plan_date = get_upcoming_sunday()
    print(f"Generating slides for upcoming Sunday: {plan_date}")

    # Initialize Pypco client
    pco = PCO(application_id=config.client_id,
              secret=config.secret)

    for stid in service_ids:
        print(f"Processing service_type_id: {stid}")

        # 1) Service Type metadata for name
        svc_resp = pco.get(f"/services/v2/service_types/{stid}")
        service_name = svc_resp["data"]["attributes"]["name"].replace(" ", "")

        # 2) Find plan for next Sunday
        plans = pco.iterate(f"/services/v2/service_types/{stid}/plans", filter="future")
        plan_obj = next(p for p in plans if p["data"]["attributes"]["sort_date"][:10] == plan_date)
        plan_id = plan_obj["data"]["id"]

        # 3) Fetch items
        items_resp = pco.get(
            f"/services/v2/service_types/{stid}/plans/{plan_id}/items",
            include="arrangement,attachments"
        )
        items = items_resp.get("data", [])
        included = items_resp.get("included", [])

        # 4) Process each item
        for item_obj in items:
            parsed = extract_items_from_pypco(item_obj, included, pco)
            if not parsed["html_present"]:
                continue

            # 4a) Build slides and write PPTX
            slides = slice_into_slides(parsed["text_chunks"])
            slides.append({"text": "", "style": "blank"})
            safe_title = parsed["title"].replace(" ", "_").replace("/", "_")
            filename = f"{plan_date}–{service_name}–Item{parsed['item_id']}-{safe_title}.pptx"
            create_pptx_for_items(slides, filename)
            print(f"  → Generated {filename}")

            # 4b) Upload binary via pco.upload()
            upload_resp = pco.upload(filename)
            upload_id = upload_resp["data"][0]["id"]
            print(f"  → Uploaded file; upload_id={upload_id}")

            # resp = pco.get(f'/services/v2/media/1477044')
            # print(resp)
            # 4c) Create a Media record using the upload ID
            media_payload = pco.template(
                'Media',
                {
                    'title': parsed['title'],
                    'media_type': 'powerpoint',
                }
            )
            media_resp = pco.post('/services/v2/media', payload=media_payload)
            media_id = media_resp['data']['id']
            print(f"  → Created Media id={media_id}")

            # 4d) Link the Media to the plan item
            link_payload = {'data': [{'type': 'Media', 'id': media_id}]}
            pco.post(
                f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{parsed['item_id']}/relationships/media",
                json=link_payload
            )
            print(f"  → Linked Media to item {parsed['item_id']}")

    print("All done.")


if __name__ == "__main__":
    main()