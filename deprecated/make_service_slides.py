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
import requests

# from deprecated.pro_generator import (
#     load_template, reset_presentation,
#     add_cue_group, add_text_cue,
#     save_pro, make_probundle
# )

CONFIG_PATH = os.getenv("SLIDES_CONFIG", "slides_config.json")

# with open("pro_templates.json", "r") as f:
#     TEMPLATE_MAP = json.load(f)

# def choose_template_key(parsed: dict) -> str:

#     # 1) Scripture readings
#     if parsed.get("is_scripture"):
#         return "Scripture Reading"
#     # 2) Any manually-named items (e.g. Centering Words, Lord's Prayer)
#     title = parsed.get("title", "").strip()
#     if title in TEMPLATE_MAP:
#         return title
#     # 3) Songs (if you ever wanted a song-specific .pro template)
#     if parsed.get("is_song"):
#         return "My Song Template"    # add if you have one
#     # 4) Everything else → either skip or use a generic template
#     return "Default Item Template"  # or raise/skip

def get_upcoming_sunday() -> str:
    today = date.today()
    days_ahead = (6 - today.weekday()) % 7
    return (today + timedelta(days=days_ahead)).isoformat()


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
from requests.auth import HTTPBasicAuth

def upload_pptx_to_media(file_path: str) -> str:
    """
    Uploads a PPTX into the org‐wide Media library.
    Returns the new Media ID as a string.
    """
    url = "https://api.planningcenteronline.com/services/v2/media"
    filename = os.path.basename(file_path)
    content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    # JSON:API “data” wrapper
    metadata = {
        "data": {
            "type": "Media",
            "attributes": {
                "title": os.path.splitext(filename)[0],
                "media_type": "Powerpoint"
            }
        }
    }

    auth = HTTPBasicAuth(config.client_id, config.secret)
    with open(file_path, "rb") as fp:
        resp = requests.post(
            url,
            auth=auth,
            files={
                "file":    (filename, fp, content_type),
                "data":    (None, json.dumps(metadata), "application/vnd.api+json")
            }
        )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


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
            
            # template_key  = choose_template_key(parsed)
            # template_path = TEMPLATE_MAP[template_key]
            # pres = load_template(template_path)
            # reset_presentation(pres, app_version=(7,16,1))

            # 4a) Build slides and write PPTX
            print(parsed)
            slides = slice_into_slides(parsed["text_chunks"])
            slides.append({"text": "", "style": "blank"})
            safe_title = parsed["title"].replace(" ", "_").replace("/", "_")
            filename = f"{plan_date}–{service_name}–Item{parsed['item_id']}-{safe_title}.pptx"
            create_pptx_for_items(
                slides,
                filename,
                scripture_reference=(parsed.get("scripture_reference") if parsed.get("is_scripture") else None)
            )
            print(f"  → Generated {filename}")

            # # 4b) Upload PPTX
            # upload_resp = pco.upload('pptxs/' + filename)
            # upload_id = upload_resp["data"][0]["id"]
            # print(f"  → Uploaded file; upload_id={upload_id}")

            # # 4c) Attach the PPTX to the item
            # attach_payload = {
            #     "data": {
            #         "attributes": {
            #             "file_upload_identifier": upload_id,
            #             "filename": filename
            #         }
            #     }
            # }

            # # 5) Create .pro file
            # template_key  = choose_template_key(parsed)
            # template_path = TEMPLATE_MAP[template_key]
            # pres = load_template(template_path)
            # reset_presentation(pres, app_version=(7,16,1))
            # group_uuid = add_cue_group(pres, parsed["title"])

            # for slide in slides:
            #     # e.g. first line as the cue label
            #     label = slide["text"].split("\n",1)[0]  
                
            #     # wrap the text in whatever RTF your template expects:
            #     # here’s a simple example using Arial 60pt
            #     rtf_payload = (
            #         r'{\rtf1\ansi\deff0'
            #         r'{\fonttbl{\f0 Arial;}}'
            #         r'\f0\fs60 '
            #         + slide["text"].replace("\n", r'\line ')
            #         + r'}'
            #     ).encode("utf-8")
                
            #     add_text_cue(pres, group_uuid, label, rtf_payload)
            
            out_name = f"{plan_date}–{service_name}–Item{parsed['item_id']}-{safe_title}.pro"
            out_path = os.path.join("output_pros", out_name)
            # save_pro(pres, out_path)
            # print(f"  → Wrote {out_path}")

            # pco.post(f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{parsed['item_id']}/attachments",
            #          payload=attach_payload)
            # print(f"  → Created attachment {filename} for item {parsed['item_id']}")

    print("All done.")


if __name__ == "__main__":
    main()