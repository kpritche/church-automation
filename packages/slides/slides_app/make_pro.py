"""
Programmatically generate ProPresenter .pro slides by cloning a template and replacing only the text and text color.

Requirements:
  • `protobuf` Python package
  • Generated Python modules from your `.proto` definitions (presentation_pb2, cue_pb2, action_pb2, slide_pb2, presentationSlide_pb2, graphicsData_pb2) in a `generated` folder on PYTHONPATH
"""
import os
import sys
import uuid
import hashlib
from copy import deepcopy

from datetime import date, timedelta
from pathlib import Path

# Allow running this file directly (python path/to/make_pro.py)
if __name__ == "__main__" and __package__ is None:
    _THIS_DIR = Path(__file__).resolve().parent
    _PKG_PARENT = _THIS_DIR.parent
    if str(_PKG_PARENT) not in sys.path:
        sys.path.insert(0, str(_PKG_PARENT))
    __package__ = "slides_app"

try:
    from church_automation_shared.paths import (
        ANNOUNCEMENTS_OUTPUT_DIR,
        SLIDES_DIR,
        SLIDES_SLIDES_CONFIG,
        SLIDES_TEMPLATES_DIR,
        SLIDES_OUTPUTS_DIR,
    )
    from church_automation_shared import config
except ModuleNotFoundError:
    from pathlib import Path
    import sys
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared.paths import (
        ANNOUNCEMENTS_OUTPUT_DIR,
        SLIDES_DIR,
        SLIDES_SLIDES_CONFIG,
        SLIDES_TEMPLATES_DIR,
        SLIDES_OUTPUTS_DIR,
    )
    from church_automation_shared import config
from pypco.pco import PCO
from .content_parser import (
    extract_items_from_pypco,
    fetch_lyrics_attachments,
    download_lyrics_pdf,
    extract_lyrics_text,
    has_pro_attachment,
)
from .slide_utils import slice_into_slides
import requests
from requests.auth import HTTPBasicAuth
import json
from .attach_images import attach_images_to_announcements

CONFIG_PATH = os.getenv("SLIDES_CONFIG", str(SLIDES_SLIDES_CONFIG))
CALL_MARKERS = ("Leader:", "L:", "Presider:", "One:", "Pastor:")
RESPONSE_MARKERS = ("People:", "P:", "All:", "Many:")

# Paths to templates
WHITE_TEMPLATE = str(SLIDES_TEMPLATES_DIR / "white_template_mac.pro")
YELLOW_TEMPLATE = str(SLIDES_TEMPLATES_DIR / "yellow_template_mac.pro")
BLANK_TEMPLATE = str(SLIDES_TEMPLATES_DIR / "blank_template_mac.pro")
JPG_FOLDER = str(ANNOUNCEMENTS_OUTPUT_DIR)

# 1) Ensure generated modules are in import path
PROTO_DIR = SLIDES_DIR / "ProPresenter7_Proto" / "generated"
if PROTO_DIR.exists():
    sys.path.insert(0, str(PROTO_DIR))

# 2) Import generated protobuf classes
import ProPresenter7_Proto.generated.presentation_pb2 as rv_presentation
from typing import List, Dict, Optional

# Aliases
Presentation = rv_presentation.Presentation

def _rtf_escape_text(value: str, formatting_codes: str = "") -> str:
    """Return an RTF-safe string for the given plain text.
    
    Args:
        value: The plain text to escape
        formatting_codes: RTF formatting codes to reapply after each line break
    """

    def _escape_codepoint(cp: int) -> str:
        return '\\u' + str(cp) + '?'

    parts = []
    for ch in value:
        codepoint = ord(ch)
        if ch == "\\":
            parts.append("\\\\")
        elif ch == "{":
            parts.append("\\{")
        elif ch == "}":
            parts.append("\\}")
        elif ch == "\r":
            continue
        elif ch == "\n":
            # After a line break, reapply formatting codes to maintain styling
            parts.append("\\line\n" + formatting_codes)
        elif ch == "\t":
            parts.append("\\tab ")
        elif 32 <= codepoint <= 126:
            parts.append(ch)
        elif codepoint <= 0xFFFF:
            parts.append(_escape_codepoint(codepoint))
        else:
            codepoint -= 0x10000
            high = 0xD800 + (codepoint >> 10)
            low = 0xDC00 + (codepoint & 0x3FF)
            parts.append(_escape_codepoint(high))
            parts.append(_escape_codepoint(low))
    return ''.join(parts)


def get_next_seven_day_window(target_date: Optional[str] = None) -> tuple[str, str]:
    """Return (start_date, end_date) ISO strings covering today through 7 days ahead inclusive.

    If target_date is provided (YYYY-MM-DD), return a window for that single date.
    """
    if target_date:
        try:
            date.fromisoformat(target_date)
        except ValueError as exc:
            raise ValueError(f"Invalid SLIDES_TARGET_DATE: {target_date}") from exc
        return (target_date, target_date)

    today = date.today()
    end = today + timedelta(days=7)
    return (today.isoformat(), end.isoformat())


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        fallback = Path(__file__).resolve().parents[3] / "slides" / "slides_config.json"
        if fallback.exists():
            with open(fallback, "r", encoding="utf-8") as f:
                return json.load(f)
        raise FileNotFoundError(f"Config file not found: {p} or {fallback}")
    with open(p, "r", encoding="utf-8") as f:
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

def load_template(path):
    pres = Presentation()
    with open(path, 'rb') as rf:
        pres.ParseFromString(rf.read())
    return pres

def make_pro_for_items(
    slides: List[Dict[str, object]],
    parsed: Dict[str, object],
    filename: str = "service_slides.pro",
    scripture_reference: Optional[str] = None,
    plan_date: Optional[str] = None
) -> None:

    wpres = load_template(WHITE_TEMPLATE)
    ypres = load_template(YELLOW_TEMPLATE)
    bpres = load_template(BLANK_TEMPLATE)

    final_pres = deepcopy(bpres)  # Start with the blank template
    final_pres.cue_groups[0].group.uuid.string = str(uuid.uuid4())  # Generate a new UUID for the cue group

    # Map bold flags by chunk text
    bold_map = {}
    for c in parsed.get('parsed_chunks', []):
        if isinstance(c, dict):
            key = c.get("text", "")
            bold_map[key] = bool(c.get("is_bold", False))
        elif isinstance(c, str):
            # text-only entry → no bold flag
            bold_map[c] = False
        # else: ignore any other types

    def add_text_slide(text: str, color: str) -> None:
        pres = deepcopy(wpres if color == 'white' else ypres)

        # Create a new cue based on the template
        template_cue = pres.cues[0]  # Use the first cue as a template
        new_cue = deepcopy(template_cue)
        new_cue.uuid.string = str(uuid.uuid4())  # Generate a new UUID for the cue
        new_cue.actions[0].uuid.string = str(uuid.uuid4())  # Generate a new UUID for the action
        new_cue.actions[0].slide.presentation.base_slide.uuid.string = str(uuid.uuid4())  # Generate a new UUID for the base_slide

        # Replace RTF placeholder
        raw_rtf = new_cue.actions[0].slide.presentation.base_slide.elements[0].element.text.rtf_data.decode('utf-8')
        parts = raw_rtf.split('replace_me')
        if len(parts) != 2:
            raise ValueError("Template missing 'replace_me' placeholder in RTF data.")

        # Extract formatting codes from the template
        # The template has formatting codes on the line before replace_me, like:
        # \f0\b\fs160 \cf2 \kerning1\expnd10\expndtw50
        # replace_me}
        # We need to extract these codes and reapply them after each \line command
        prefix = parts[0]
        last_newline_idx = prefix.rfind('\n')
        
        if last_newline_idx != -1 and last_newline_idx > 0:
            # Find the previous newline (or start of string)
            prev_newline_idx = prefix.rfind('\n', 0, last_newline_idx)
            if prev_newline_idx != -1:
                # Extract everything between the two newlines (the formatting line)
                formatting_codes = prefix[prev_newline_idx + 1:last_newline_idx].strip()
            else:
                # No previous newline, so extract from start to last newline
                formatting_codes = prefix[:last_newline_idx].strip()
                # Get only the last line of formatting codes if there are multiple lines
                formatting_lines = formatting_codes.split('\n')
                formatting_codes = formatting_lines[-1] if formatting_lines else ""
        else:
            # Fallback: try to find RTF commands at the end of prefix
            formatting_codes = ""
            tokens = prefix.split()
            # Find the last sequence of RTF commands (starting with backslash)
            for i in range(len(tokens) - 1, -1, -1):
                if tokens[i].startswith('\\') and not tokens[i].startswith('\\pard'):
                    # Found start of formatting commands
                    formatting_codes = ' '.join(tokens[i:])
                    break

        # Add newline after formatting codes for proper RTF structure
        if formatting_codes and not formatting_codes.endswith('\n'):
            formatting_codes += '\n'

        rtf_text = _rtf_escape_text(text.upper(), formatting_codes)
        new_rtf = (parts[0] + rtf_text + parts[1]).encode('utf-8')
        new_cue.actions[0].slide.presentation.base_slide.elements[0].element.text.rtf_data = new_rtf
        
        # Add new slide
        final_pres.cues.append(new_cue)
        new_cue_id = final_pres.cue_groups[0].cue_identifiers.add()
        new_cue_id.string = new_cue.uuid.string
    
    if scripture_reference:
        # Add scripture reference slide
        add_text_slide(scripture_reference, "white")
    
    for slide in slides:
        text = slide.get('text', '').strip()
    
        if slide.get('style') == 'blank' or not text:
            # blank slide
            add_text_slide('', 'white')
            continue

        # Determine color for THIS slide based on its content
        # 1) Lead-speaker lines remain white…
        if any(text.startswith(m) for m in CALL_MARKERS):
            slide_color = "white"
        # 2) Response markers OR bolded text become yellow…
        elif any(text.startswith(m) for m in RESPONSE_MARKERS) or slide.get("is_bold", False):
            slide_color = "yellow"
        # 3) All other text is white (default)
        else:
            slide_color = "white"
        
        add_text_slide(text, slide_color)
    
    # Write out
    out_dir = SLIDES_OUTPUTS_DIR / plan_date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    with open(out_path, 'wb') as wf:
        wf.write(final_pres.SerializeToString())


def _generate_content_hash(text_chunks: List[str], title: str) -> str:
    """Generate a hash of the content for caching duplicate items.
    
    Returns a hash string based on the item title and text chunks,
    so items with the same content across services will have the same hash.
    """
    content_str = f"{title}|" + "|".join(text_chunks)
    return hashlib.sha256(content_str.encode()).hexdigest()[:8]


def main():
    cfg = load_config(CONFIG_PATH)
    service_ids = cfg.get("service_type_ids", [])
    if not service_ids:
        raise ValueError(f"No service_type_ids in config: {CONFIG_PATH}")
    
    target_date = os.getenv("SLIDES_TARGET_DATE")
    start_date, end_date = get_next_seven_day_window(target_date)
    if target_date:
        print(f"Generating slides for services on {target_date}")
    else:
        print(f"Generating slides for services between {start_date} and {end_date}")

    # Initialize Pypco client
    pco = PCO(application_id=config.client_id, secret=config.secret)
    processed_dates = set()
    
    # Cache: maps content hash -> (file_path, plan_date, parsed_data)
    # This prevents generating duplicate .pro files for items that appear in multiple services
    content_cache: Dict[str, tuple] = {}

    for stid in service_ids:
        print(f"Processing service type ID: {stid}")

        # Use service type metadata for name
        svc_resp = pco.get(f"/services/v2/service_types/{stid}")
        service_name = svc_resp["data"]["attributes"]["name"].replace(" ","")

        # Find all plans within the next 7 days window
        plans = pco.iterate(f"/services/v2/service_types/{stid}/plans", filter="future")
        selected = []
        for plan in plans:
            sort_date = plan["data"]["attributes"].get("sort_date", "")
            plan_date = sort_date[:10] if sort_date else ""
            if plan_date and (start_date <= plan_date <= end_date):
                selected.append((plan, plan_date))

        if not selected:
            print(f"No plans scheduled for {service_name} ({stid}) between {start_date} and {end_date}; skipping.")
            continue

        for plan_obj, plan_date in selected:
            plan_id = plan_obj["data"]["id"]

            # Fetch items
            items_resp = pco.get(
                f"/services/v2/service_types/{stid}/plans/{plan_id}/items",
                include="arrangement,attachments"
            )
            items = items_resp.get("data", [])
            included = items_resp.get("included", [])
            # print(items)

            # Process each item
            for item_obj in items:
                parsed = extract_items_from_pypco(item_obj, included, pco)

                # Skip if no HTML content, unless it's a song (which we'll try to fetch lyrics for)
                if not parsed["html_present"] and not parsed.get("is_song"):
                    continue

                # Check if a .pro file is already attached to this item
                if has_pro_attachment(pco, stid, plan_id, parsed['item_id']):
                    print(f"[SKIP] Item already has .pro file attached: {parsed['title']}")
                    continue

                # Build raw and bold-aware slides
                print(f"Generating slides for item: {parsed['title']} on {plan_date}")
                raw_chunks = parsed['parsed_chunks']

                # For songs, try to fetch and use lyrics from PDF attachment
                chunks = parsed["text_chunks"]
                if parsed.get("is_song"):
                    print(f"  > Song detected: {parsed['title']}")
                    # Fetch lyrics attachments
                    lyrics_items = [{"item_obj": item_obj, "title": parsed['title']}]
                    lyrics_attachments = fetch_lyrics_attachments(
                        pco,
                        lyrics_items,
                        stid,
                        plan_id,
                        included,
                    )
                    
                    if lyrics_attachments:
                        # Download and extract lyrics from the first attachment
                        att_info = lyrics_attachments[0]
                        attachment_obj = att_info["attachment_obj"]
                        item_id = att_info["item_id"]
                        
                        pdf_bytes = download_lyrics_pdf(
                            attachment_obj,
                            pco,
                            stid,
                            plan_id,
                            item_id,
                        )
                        
                        if pdf_bytes:
                            lyrics_text = extract_lyrics_text(pdf_bytes, parsed['title'])
                            if lyrics_text:
                                print(f"  [OK] Extracted lyrics from PDF")
                                # Split lyrics into lines for processing
                                chunks = [line.strip() for line in lyrics_text.split('\n') if line.strip()]
                            else:
                                print(f"  [WARN] Failed to extract text from lyrics PDF, using fallback HTML")
                        else:
                            print(f"  [WARN] Failed to download lyrics PDF, using fallback HTML")
                    else:
                        print(f"  [INFO] No lyrics.pdf attachment found, using fallback HTML")
                    
                    # Group every two lines into one chunk for song display
                    if chunks:
                        grouped_chunks = []
                        for i in range(0, len(chunks), 2):
                            pair = chunks[i:i+2]
                            grouped_chunks.append("\n".join(pair))
                        chunks = grouped_chunks

                # 2) Slice into slides with call/response prefixes respected
                slides = slice_into_slides(
                    chunks,
                    max_chars=33,
                    max_lines=2,
                    force_new_slide_prefixes=list(CALL_MARKERS) + list(RESPONSE_MARKERS),
                )

                # 3) Build a lookup of which chunks were bold in your HTML
                bold_map = {}
                for c in parsed.get('parsed_chunks', []):
                    if isinstance(c, dict):
                        key = c.get("text", "")
                        bold_map[key] = bool(c.get("is_bold", False))
                    elif isinstance(c, str):
                        bold_map[c] = False

                # 4) Annotate each slide dict with its bold‐flag
                for slide in slides:
                    slide["is_bold"] = bold_map.get(slide["text"], False)

                slides.append({'text': '', 'style': 'blank', 'is_bold': False})

                # Generate a content hash for caching
                content_hash = _generate_content_hash(parsed.get("text_chunks", []), parsed["title"])
                
                safe_title = parsed["title"].strip().replace(" ", "_").replace("/", "_")
                
                # Check if we've already generated this content
                if content_hash in content_cache:
                    cached_file, cached_date, _ = content_cache[content_hash]
                    print(f"[CACHE HIT] Reusing {cached_file.name} (first generated on {cached_date})")
                    out_dir = SLIDES_OUTPUTS_DIR / plan_date
                    out_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Verify cached file still exists
                    if cached_file.exists():
                        # Upload the existing cached file to this item
                        upload_resp = pco.upload(str(cached_file))
                        upload_id = upload_resp["data"][0]["id"]
                        attach_payload = {
                            "data": {
                                "attributes": {
                                    "file_upload_identifier": upload_id,
                                    "filename": cached_file.name
                                }
                            }
                        }
                        pco.post(
                            f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{parsed['item_id']}/attachments",
                            payload=attach_payload
                        )
                        print(f"  > Uploaded cached file; upload_id={upload_id}")
                    else:
                        print(f"  [WARN] Cached file not found, regenerating...")
                        content_cache.pop(content_hash, None)
                else:
                    # Generate new file
                    # Use a generic filename without service name for shared items
                    filename = f"{plan_date}-{safe_title}-{content_hash}.pro"
                    out_dir = SLIDES_OUTPUTS_DIR / plan_date
                    out_dir.mkdir(parents=True, exist_ok=True)

                    make_pro_for_items(
                        slides,
                        parsed,
                        filename,
                        scripture_reference=(parsed.get("scripture_reference") if parsed.get("is_scripture") else None),
                        plan_date=plan_date
                    )
                    print(f"Generated slides for service type ID {stid} into {filename}")
                    
                    out_path = out_dir / filename
                    
                    # Cache this file
                    content_cache[content_hash] = (out_path, plan_date, parsed)

                    # Upload the generated .pro file to its item
                    upload_resp = pco.upload(str(out_path))
                    upload_id = upload_resp["data"][0]["id"]
                    attach_payload = {
                        "data": {
                            "attributes": {
                                "file_upload_identifier": upload_id,
                                "filename": filename
                            }
                        }
                    }
                    pco.post(
                        f"/services/v2/service_types/{stid}/plans/{plan_id}/items/{parsed['item_id']}/attachments",
                        payload=attach_payload
                    )
                    print(f"  > Uploaded file; upload_id={upload_id}")

            processed_dates.add(plan_date)

    # # Attach images for each processed date
    # for d in sorted(processed_dates):
    #     attach_images_to_announcements(JPG_FOLDER + f"/{d}")
    # print("All slides generated and uploaded successfully for the next 7 days.")



if __name__ == "__main__":
    main()
