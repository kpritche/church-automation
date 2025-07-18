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
    
import os, json, requests
from requests.auth import HTTPBasicAuth
import config  # contains client_id & secret (or PAT)

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

            # 4a) Build slides and write PPTX
            slides = slice_into_slides(parsed["text_chunks"])
            slides.append({"text": "", "style": "blank"})
            safe_title = parsed["title"].replace(" ", "_").replace("/", "_")
            filename = f"{plan_date}–{service_name}–Item{parsed['item_id']}-{safe_title}.pptx"
            create_pptx_for_items(slides, filename)
            print(f"  → Generated {filename}")

            # media_id = upload_pptx_to_media(filename)
            # print(f"Uploaded Media → ID {media_id}")

            # 4b) Create a Media record using the upload ID
            media_payload = {
                'data': {
                    'type': 'Media',
                    'attributes':{
                    'title': parsed['title'],
                    'media_type': 'Powerpoint',
                    }
                }
            }
            with open(filename, 'rb') as f:
                media_resp = request.post('/services/v2/media', 
                             files = {
                                    'file': (os.path.basename(filename), f, 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
                                    'data': (None, json.dumps(media_payload), 'application/vnd.api+json')
                }
            )

            media_id = media_resp['data']['id']
            print(f"  → Created Media id={media_id}")

            # # 4c) Upload binary via pco.upload()
            # upload_resp = pco.upload(filename)
            # upload_id = upload_resp["data"][0]["id"]
            # print(f"  → Uploaded file; upload_id={upload_id}")

            # # 4d) Link the Media to the plan item
            # link_payload = {'data': 
            #                     {'type': 'Attachment',
            #                      'attributes': 
            #                         {'content_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            #                          'filename': filename
            #                          }
            #                     }
            # }

            # with open(filename, 'rb') as f:
            #     files = {'file': (os.path.basename(filename), f, link_payload["data"]["attributes"]["content_type"]),
            #              'data': (None, json.dumps(link_payload), "aplication/vnd.api+json")
            #     }
            #     print(parsed['item_id'])
            #     resp = pco.patch(
            #         f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{parsed['item_id']}/attachments",
            #         files=files
            #     )

            # print(f"  → Created attachment:", resp['data'][0]['id'])
            break  # Break after first item for demo purposes

    print("All done.")


if __name__ == "__main__":
    main()