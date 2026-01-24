"""ProPresenter 7 announcement file generator.

Generates .pro files (protobuf binary) from announcement data by cloning
a template slide and populating it with dynamic content.

Based on the working patterns from slides_app/make_pro.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import uuid as uuid_module
from copy import deepcopy
from pathlib import Path
from typing import List, Optional

import qrcode
import requests

# Setup paths for proto imports
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROTO_PATH = REPO_ROOT / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
if str(PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(PROTO_PATH))

# Import protobuf modules
import presentation_pb2

# Template paths
TEMPLATE_DIR = REPO_ROOT / "packages" / "announcements" / "templates"
ANNOUNCEMENT_TEMPLATE = TEMPLATE_DIR / "announcement_template" / "announcement_template.pro"
BLANK_TEMPLATE = TEMPLATE_DIR / "blank_template_mac.pro"

# Placeholder text in the template RTF
TITLE_PLACEHOLDER = "title_text"
BODY_PLACEHOLDER = "body_text"


def _rtf_escape_text(value: str) -> str:
    """Return an RTF-safe string for the given plain text.
    
    Matches the implementation from make_pro.py for consistency.
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
            parts.append("\\line ")
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


def load_template(path: Path) -> presentation_pb2.Presentation:
    """Load a .pro template file."""
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    
    pres = presentation_pb2.Presentation()
    with open(path, 'rb') as f:
        pres.ParseFromString(f.read())
    return pres


def download_image(url: str, dest_dir: Path) -> Optional[Path]:
    """Download an image from a URL to a local directory."""
    if not url:
        return None
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '')
        if 'png' in content_type or url.lower().endswith('.png'):
            ext = '.png'
        elif 'gif' in content_type or url.lower().endswith('.gif'):
            ext = '.gif'
        else:
            ext = '.jpg'
        
        filename = f"img_{str(uuid_module.uuid4())[:8]}{ext}"
        filepath = dest_dir / filename
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
            
        return filepath
    except Exception as e:
        print(f"   [WARN] Failed to download image from {url}: {e}")
        return None


def generate_qr_image(link: str, output_path: Path) -> Path:
    """Generate a QR code image and save it."""
    qr = qrcode.QRCode(border=1)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(output_path), format="PNG")
    return output_path


def find_element_by_name(elements, name: str):
    """Find an element wrapper by its name field."""
    for elem_wrapper in elements:
        if elem_wrapper.HasField('element'):
            if elem_wrapper.element.name == name:
                return elem_wrapper
    return None


def update_media_element(element, image_path: Path) -> None:
    """Update a media element's URL to point to a local image."""
    if element.HasField('fill') and element.fill.HasField('media'):
        media = element.fill.media
        media.uuid.string = str(uuid_module.uuid4()).upper()
        
        abs_path = str(image_path.resolve()).replace("\\", "/")
        media.url.absolute_string = f"file:///{abs_path}"
        media.url.local.path = str(image_path.name)
        
        ext = image_path.suffix.lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        media.metadata.format = ext


def replace_rtf_placeholder(rtf_bytes: bytes, placeholder: str, new_text: str) -> bytes:
    """Replace a placeholder in RTF data with escaped text.
    
    This preserves the RTF formatting while only replacing the text content.
    """
    rtf_str = rtf_bytes.decode('utf-8')
    
    if placeholder not in rtf_str:
        return rtf_bytes
    
    escaped_text = _rtf_escape_text(new_text)
    new_rtf = rtf_str.replace(placeholder, escaped_text)
    return new_rtf.encode('utf-8')


def generate_pro_file(announcements: List[dict], output_path: str) -> None:
    """Generate a ProPresenter .pro file from announcement data.
    
    Args:
        announcements: List of announcement dictionaries with keys:
            - title: str
            - body: str  
            - image_url: str (optional)
            - link: str (optional, for QR code)
        output_path: Path to save the output .pro file
    """
    print(f"   Loading templates...")
    print(f"      Blank: {BLANK_TEMPLATE}")
    print(f"      Announcement: {ANNOUNCEMENT_TEMPLATE}")
    
    # Load both templates
    blank_pres = load_template(BLANK_TEMPLATE)
    announcement_pres = load_template(ANNOUNCEMENT_TEMPLATE)
    
    # Start with a deep copy of the blank template (keeps structure intact)
    final_pres = deepcopy(blank_pres)
    
    # Generate new UUID for the presentation and cue group
    final_pres.uuid.string = str(uuid_module.uuid4()).upper()
    final_pres.name = "Weekly Announcements"
    
    if len(final_pres.cue_groups) > 0:
        final_pres.cue_groups[0].group.uuid.string = str(uuid_module.uuid4()).upper()
    
    # Get the announcement template's first cue as our slide template
    if len(announcement_pres.cues) == 0:
        raise ValueError("Announcement template has no cues/slides")
    template_cue = announcement_pres.cues[0]
    
    # Create temp directory for downloaded images
    temp_dir = Path(tempfile.mkdtemp(prefix="propresenter_"))
    print(f"   Temp directory: {temp_dir}")
    
    try:
        for idx, ann in enumerate(announcements, 1):
            title = ann.get('title', 'Untitled')
            body = ann.get('body', ann.get('summary', ''))
            image_url = ann.get('image_url', '')
            link = ann.get('link', '')
            
            print(f"   [{idx}/{len(announcements)}] {title[:40]}...")
            
            # Deep copy the template cue
            new_cue = deepcopy(template_cue)
            
            # Generate new UUIDs for the cue, action, and slide
            new_cue.uuid.string = str(uuid_module.uuid4()).upper()
            
            if len(new_cue.actions) > 0:
                new_cue.actions[0].uuid.string = str(uuid_module.uuid4()).upper()
                
                if new_cue.actions[0].HasField('slide'):
                    slide_action = new_cue.actions[0].slide
                    if slide_action.HasField('presentation'):
                        pres_slide = slide_action.presentation
                        if pres_slide.HasField('base_slide'):
                            pres_slide.base_slide.uuid.string = str(uuid_module.uuid4()).upper()
                            
                            # Process each element
                            for elem_wrapper in pres_slide.base_slide.elements:
                                if elem_wrapper.HasField('element'):
                                    elem = elem_wrapper.element
                                    elem.uuid.string = str(uuid_module.uuid4()).upper()
                                    
                                    # Update media UUID if present
                                    if elem.HasField('fill') and elem.fill.HasField('media'):
                                        elem.fill.media.uuid.string = str(uuid_module.uuid4()).upper()
                                    
                                    # Replace text placeholders
                                    if elem.HasField('text'):
                                        rtf_data = elem.text.rtf_data
                                        
                                        # Check for title placeholder
                                        if TITLE_PLACEHOLDER in rtf_data.decode('utf-8', errors='ignore'):
                                            elem.text.rtf_data = replace_rtf_placeholder(
                                                rtf_data, TITLE_PLACEHOLDER, title
                                            )
                                        
                                        # Check for body placeholder
                                        elif BODY_PLACEHOLDER in rtf_data.decode('utf-8', errors='ignore'):
                                            elem.text.rtf_data = replace_rtf_placeholder(
                                                rtf_data, BODY_PLACEHOLDER, body
                                            )
                                    
                                    # Update image element
                                    if elem.name == "image" and image_url:
                                        local_img = download_image(image_url, temp_dir)
                                        if local_img:
                                            update_media_element(elem, local_img)
                                    
                                    # Update QR code element
                                    if elem.name == "qr_code" and link:
                                        qr_path = temp_dir / f"qr_{idx}.png"
                                        generate_qr_image(link, qr_path)
                                        update_media_element(elem, qr_path)
            
            # Add the new cue to the presentation
            final_pres.cues.append(new_cue)
            
            # CRITICAL: Register the cue in cue_identifiers
            if len(final_pres.cue_groups) > 0:
                cue_id = final_pres.cue_groups[0].cue_identifiers.add()
                cue_id.string = new_cue.uuid.string
        
        # Serialize and save
        output_data = final_pres.SerializeToString()
        
        with open(output_path, 'wb') as f:
            f.write(output_data)
        
        print(f"   [OK] Generated {len(announcements)} slides")
        print(f"   [OK] Saved to: {output_path}")
        print(f"   [OK] File size: {len(output_data):,} bytes")
        
    finally:
        print(f"   [INFO] Image assets saved to: {temp_dir}")


def main():
    """Test the generator with sample data."""
    test_announcements = [
        {
            "title": "Community Dinner",
            "body": "Join us for a wonderful evening of fellowship! We'll have great food, music, and time to connect with one another.",
            "image_url": "",
            "link": "https://fumcwl.org/dinner"
        },
        {
            "title": "Youth Group Retreat",
            "body": "Our annual youth retreat is coming up! Sign up now to reserve your spot. Cost is $50 per person.",
            "image_url": "",
            "link": "https://fumcwl.org/youth"
        },
    ]
    
    output_path = REPO_ROOT / "packages" / "announcements" / "output" / "test_announcements.pro"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("ProPresenter Announcement Generator - Test Run")
    print("=" * 60)
    
    generate_pro_file(test_announcements, str(output_path))
    
    print("\n" + "=" * 60)
    print("[OK] Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
