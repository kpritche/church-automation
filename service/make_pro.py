"""
Programmatically generate ProPresenter .pro slides by cloning a template and replacing only the text and text color.

Usage:
  python use_template.py --template template.txt --output_dir output_slides

Requirements:
  • `protobuf` Python package
  • Generated Python modules from your `.proto` definitions (presentation_pb2, cue_pb2, action_pb2, slide_pb2, presentationSlide_pb2, graphicsData_pb2) in a `generated` folder on PYTHONPATH
"""
import os
import sys
import uuid
from argparse import ArgumentParser
from google.protobuf.message import DecodeError
from google.protobuf import text_format
from copy import deepcopy

from datetime import date, timedelta

import config
from pypco.pco import PCO
from content_parser import extract_items_from_pypco
from slide_utils import slice_into_slides
from ppt_generator_services import create_pptx_for_items
import requests
from requests.auth import HTTPBasicAuth
import json

CONFIG_PATH = os.getenv("SLIDES_CONFIG", "slides_config.json")
CALL_MARKERS = ("Leader:", "L:")
RESPONSE_MARKERS = ("People:", "P:")

# 1) Ensure generated modules are in import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ProPresenter7_Proto', 'generated'))

# 2) Import generated protobuf classes
import ProPresenter7_Proto.generated.presentation_pb2 as rv_presentation
import ProPresenter7_Proto.generated.cue_pb2         as rv_cue
import ProPresenter7_Proto.generated.action_pb2      as rv_action
import ProPresenter7_Proto.generated.presentationSlide_pb2 as rv_pslide
import ProPresenter7_Proto.generated.slide_pb2       as rv_slide
import ProPresenter7_Proto.generated.graphicsData_pb2 as rv_graphics
import ProPresenter7_Proto.generated.applicationInfo_pb2 as rv_ainfo
from typing import List, Dict, Optional

# Aliases
Presentation      = rv_presentation.Presentation
Action            = rv_action.Action
PresentationSlide = rv_pslide.PresentationSlide
ApplicationInfo   = rv_ainfo.ApplicationInfo

def get_upcoming_sunday() -> str:
    today = date.today()
    days_ahead = (6 - today.weekday()) % 7
    return (today + timedelta(days=days_ahead)).isoformat()


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def upload_pro_to_media(file_path: str) -> str:
    """
    Uploads a PPTX into the org-wide Media library.
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

def make_pro_for_items(
    slides: List[Dict[str, str]],
    filename: str = "service_slides.pro",
    scripture_reference: Optional[str] = None,
    plan_date: Optional[str] = None
) -> None:
    
    
    # Load the template presentation
    white_template_path = "templates/white_template_mac.pro"
    wpres = Presentation()
    with open(white_template_path, "rb") as f:
        wpres.ParseFromString(f.read())

    yellow_template_path = "templates/yellow_template_mac.pro"
    ypres = Presentation()
    with open(yellow_template_path, "rb") as f:
        ypres.ParseFromString(f.read())
    
    blank_template_path = "templates/blank_template_mac.pro"
    bpres = Presentation()
    with open(blank_template_path, "rb") as f:
        bpres.ParseFromString(f.read())

    final_pres = deepcopy(bpres)  # Start with the blank template
    final_pres.cue_groups[0].group.uuid.string = str(uuid.uuid4())  # Generate a new UUID for the cue group
    # final_pres.cues.clear()  # Clear existing cues to start fresh
    # final_pres.cue_groups[0].cue_identifiers.clear()  # Clear existing cue identifiers

    def add_text_slide(slide_text: str, color: str) -> None:
        if color == "white":
            pres = deepcopy(wpres)
        if color == "yellow":
            pres = deepcopy(ypres)

        # Create a new cue based on the template
        template_cue = pres.cues[0]  # Use the first cue as a template
        new_cue = deepcopy(template_cue)
        new_cue.uuid.string = str(uuid.uuid4())  # Generate a new UUID for the cue
        new_cue.actions[0].uuid.string = str(uuid.uuid4())  # Generate a new UUID for the action
        new_cue.actions[0].slide.presentation.base_slide.uuid.string = str(uuid.uuid4())  # Generate a new UUID for the base_slide

        # Modify the rtf_data element in the new cue
        text = new_cue.actions[0].slide.presentation.base_slide.elements[0].element.text.rtf_data
        text = text.decode("utf-8")
        text_split = text.split('replace_me')
        new_text = f'{slide_text}'
        new_text = text_split[0] + new_text.upper() + text_split[1]
        
        new_rtf = new_text.encode("utf-8")
        new_cue.actions[0].slide.presentation.base_slide.elements[0].element.text.rtf_data = new_rtf

        # Add new slide
        final_pres.cues.append(new_cue)
        new_cue_id = final_pres.cue_groups[0].cue_identifiers.add()
        new_cue_id.string = new_cue.uuid.string
    
 

    current_color = "white"  # Start with white slides
    
    if scripture_reference:
        # Add scripture reference slide
        add_text_slide(scripture_reference, "white")
        print(scripture_reference)
    
    for slide in slides:
        text = slide.get('text', '').strip()
    
        if slide.get('style') == 'blank' or not text:
            pres = deepcopy(bpres)
            template_cue = pres.cues[0]
            new_cue = deepcopy(template_cue)
            new_cue.uuid.string = str(uuid.uuid4())
            final_pres.cues.append(new_cue)
            new_cue_id = final_pres.cue_groups[0].cue_identifiers.add()
            new_cue_id.string = new_cue.uuid.string
            continue

        if any(text.startswith(m) for m in CALL_MARKERS):
            current_color = "white"
        elif any(text.startswith(m) for m in RESPONSE_MARKERS):
            current_color = "yellow"
        
        add_text_slide(text, current_color)
    
    
    # Add a blank slide at the end
    pres = deepcopy(bpres)
    template_cue = pres.cues[0]  # Use the first cue as a template
    new_cue = deepcopy(template_cue)
    new_cue.uuid.string = str(uuid.uuid4())
    final_pres.cues.append(new_cue)
    new_cue_id = final_pres.cue_groups[0].cue_identifiers.add()
    new_cue_id.string = new_cue.uuid.string

    # Save the modified presentation
    out_path = f"outputs/{plan_date}/{filename}"
    with open(out_path, "wb") as f:
        f.write(final_pres.SerializeToString())

def main():
    cfg = load_config(CONFIG_PATH)
    service_ids = cfg.get("service_type_ids", [])
    if not service_ids:
        raise ValueError(f"No service_type_ids in config: {CONFIG_PATH}")
    
    plan_date = get_upcoming_sunday()
    print(f"Generating slides for upcoming Sunday: {plan_date}")
    
    # Ensure output directory exists
    output_dir = f'outputs/{plan_date}'
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Directory created or already exists: {output_dir}")
    except Exception as e:
        print(f"Failed to create directory: {output_dir}. Error: {e}")
        raise

    # Initialize Pypco client
    pco = PCO(application_id=config.client_id, secret=config.secret)

    for stid in service_ids:
        print(f"Processing service type ID: {stid}")

        # Use service type metadata for name
        svc_resp = pco.get(f"/services/v2/service_types/{stid}")
        service_name = svc_resp["data"]["attributes"]["name"].replace(" ","")

        # Find plan for next Sunday
        plans = pco.iterate(f"/services/v2/service_types/{stid}/plans", filter="future")
        plan_obj = next(p for p in plans if p["data"]["attributes"]["sort_date"][:10] == plan_date)
        plan_id = plan_obj["data"]["id"]

        # Fetch items
        items_resp = pco.get(f"/services/v2/service_types/{stid}/plans/{plan_id}/items",
                             include="arrangement,attachments"
        )
        items = items_resp.get("data", [])
        included = items_resp.get("included", [])

        # Process each item
        for item_obj in items:
            parsed = extract_items_from_pypco(item_obj, included, pco)
            
            if not parsed["html_present"]:
                continue
            
            slides = slice_into_slides(parsed["text_chunks"], max_chars=33, max_lines=2)
            slides.append({"text": "", "style":"blank"}
                          )
            safe_title = parsed["title"].strip().replace(" ", "_").replace("/", "_")
            filename = f"{plan_date}-{service_name}-{safe_title}.pro"
            

            make_pro_for_items(
                slides,
                filename,
                scripture_reference=(parsed.get("scripture_reference") if parsed.get("is_scripture") else None),
                plan_date=plan_date
            )
            print(f"Generated slides for service type ID {stid} into {filename}")

            # Upload the generated .pro file to its item
            uplaod_resp = pco.upload(f'outputs/{plan_date}/' + filename)
            upload_id = uplaod_resp["data"][0]["id"]
            attach_payload = {
                "data": {
                    "attributes": {
                        "file_upload_identifier": upload_id,
                        "filename": filename
                    }
                }
            }
            pco.post(f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{parsed['item_id']}/attachments",
                    payload=attach_payload)
            print(f"  → Uploaded file; upload_id={upload_id}")
    print("All slides generated and uploaded successfully.")



if __name__ == "__main__":
    main()