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
import zipfile
import shutil
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
ANNOUNCEMENT_TEMPLATE = TEMPLATE_DIR / "announcement_template_mac" / "announcement_template.pro"
BLANK_TEMPLATE = TEMPLATE_DIR / "blank_template_mac.pro"
# Optional: A .probundle containing static template assets (logo, backgrounds, etc.)
# Export this from ProPresenter on Mac to include all referenced assets
TEMPLATE_ASSETS_BUNDLE = TEMPLATE_DIR / "weekly_announcements_2026-01-25_corrected.proBundle"

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
    """Generate a QR code image and save it.
    
    Generates a larger QR code (approximately 800x800 pixels) for better
    compatibility with ProPresenter on Mac.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,  # Larger box size for higher resolution
        border=4,
    )
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


def update_media_element(element, image_path: Path, propresenter_assets_path: str = None) -> None:
    """Update a media element's URL to point to a local image.
    
    Args:
        element: The protobuf element to update
        image_path: Path to the image file
        propresenter_assets_path: The ProPresenter Media/Assets path for absolute_string
    """
    import basicTypes_pb2
    from PIL import Image
    
    if element.HasField('fill') and element.fill.HasField('media'):
        media = element.fill.media
        media.uuid.string = str(uuid_module.uuid4()).upper()
        
        # Set platform to macOS (user enforced)
        media.url.platform = basicTypes_pb2.URL.PLATFORM_MACOS
        
        if propresenter_assets_path:
            # For bundles: use ProPresenter's expected path format
            full_path = f"{propresenter_assets_path}/{image_path.name}"
            media.url.absolute_string = full_path
            
            # local: relative path with root set to ROOT_SHOW
            media.url.local.root = basicTypes_pb2.URL.LocalRelativePath.ROOT_SHOW
            media.url.local.path = f"Media/Assets/{image_path.name}"
        else:
            # For standalone files, use absolute path
            abs_path = str(image_path.resolve()).replace("\\", "/")
            media.url.absolute_string = f"file:///{abs_path}"
            media.url.local.path = str(image_path.name)
        
        # Set format metadata
        ext = image_path.suffix.lower().lstrip('.')
        if ext == 'jpg':
            ext = 'jpeg'
        media.metadata.format = ext
        
        # Read actual image dimensions and update natural_size
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                # Update the image drawing natural_size
                media.image.drawing.natural_size.width = float(width)
                media.image.drawing.natural_size.height = float(height)
        except Exception as e:
            print(f"      Warning: Could not read image dimensions for {image_path.name}: {e}")


def fix_all_media_paths(presentation, assets_path_prefix: str) -> None:
    """Updates absolute_string for ALL media elements to match production path.
    
    This ensures that even static elements from the template (logos, backgrounds)
    use the correct production file path and macOS platform setting.
    """
    import basicTypes_pb2
    
    for cue in presentation.cues:
        for action in cue.actions:
            if action.HasField('slide') and action.slide.HasField('presentation'):
                slide = action.slide.presentation
                if slide.HasField('base_slide'):
                    for elem_wrapper in slide.base_slide.elements:
                        if elem_wrapper.HasField('element'):
                            elem = elem_wrapper.element
                            if elem.HasField('fill') and elem.fill.HasField('media'):
                                media = elem.fill.media
                                
                                # Enforce macOS platform
                                media.url.platform = basicTypes_pb2.URL.PLATFORM_MACOS
                                
                                # Extract filename and rebuild absolute path
                                if media.url.HasField('local') and media.url.local.path:
                                    filename = Path(media.url.local.path).name
                                    full_path = f"{assets_path_prefix}/{filename}"
                                    media.url.absolute_string = full_path
                                    
                                    # Ensure local path has correct prefix
                                    # This handles cases where template might have just "logo.png"
                                    if not media.url.local.path.replace("\\", "/").startswith("Media/Assets/"):
                                        media.url.local.path = f"Media/Assets/{filename}"
                                        media.url.local.root = basicTypes_pb2.URL.LocalRelativePath.ROOT_SHOW


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


def generate_pro_file(announcements: List[dict], output_path: str, as_bundle: bool = False) -> None:
    """Generate a ProPresenter file (.pro or .probundle).
    
    Args:
        announcements: List of announcement data
        output_path: Destination path
        as_bundle: If True, creates a .probundle (zip) with assets
    """
    output_path = Path(output_path)
    print(f"   Loading templates...")
    print(f"      Blank: {BLANK_TEMPLATE}")
    print(f"      Announcement: {ANNOUNCEMENT_TEMPLATE}")
    
    # Load both templates
    blank_pres = load_template(BLANK_TEMPLATE)
    announcement_pres = load_template(ANNOUNCEMENT_TEMPLATE)
    
    # Start with a deep copy of the blank template (keeps structure intact)
    final_pres = deepcopy(blank_pres)
    
    # Copy application version info from announcement template to match newer version
    if announcement_pres.HasField('application_info'):
        final_pres.application_info.CopyFrom(announcement_pres.application_info)
    
    # Generate new UUID for the presentation and cue group
    final_pres.uuid.string = str(uuid_module.uuid4()).upper()
    final_pres.name = "Weekly Announcements"
    
    if len(final_pres.cue_groups) > 0:
        final_pres.cue_groups[0].group.uuid.string = str(uuid_module.uuid4()).upper()
    
    # Get the announcement template's first cue as our slide template
    if len(announcement_pres.cues) == 0:
        raise ValueError("Announcement template has no cues/slides")
    template_cue = announcement_pres.cues[0]
    
    # Working directory (temp)
    # If bundling, we need a persistent structure to zip
    work_dir_obj = tempfile.TemporaryDirectory(prefix="propresenter_")
    work_dir = Path(work_dir_obj.name)
    print(f"   Working directory: {work_dir}")
    
    try:
        # For bundles, create Media subdirectory matching ProPresenter's structure
        if as_bundle:
            media_dir = work_dir / "Media"
            media_dir.mkdir(exist_ok=True)
            # ProPresenter expects absolute path to its Media/Assets folder
            # User specified production path on Mac
            propresenter_assets_path = "file:///Users/fcproduction/Documents/ProPresenter/Media/Assets"
            
            # Extract static template assets from template bundle if available
            if TEMPLATE_ASSETS_BUNDLE.exists():
                print(f"   Extracting template assets from {TEMPLATE_ASSETS_BUNDLE.name}...")
                with zipfile.ZipFile(TEMPLATE_ASSETS_BUNDLE, 'r') as z:
                    for name in z.namelist():
                        # Extract only Media files (not .pro or PDF)
                        if name.startswith('Media/') and not name.endswith('/'):
                            # Extract to our media_dir
                            filename = Path(name).name
                            dest_path = media_dir / filename
                            # Don't overwrite if file already exists (dynamic content takes priority)
                            if not dest_path.exists():
                                with z.open(name) as src, open(dest_path, 'wb') as dst:
                                    dst.write(src.read())
                print(f"   Extracted template assets to {media_dir}")
        else:
            media_dir = work_dir
            propresenter_assets_path = None
        
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
                                        local_img = download_image(image_url, media_dir)
                                        if local_img:
                                            update_media_element(elem, local_img, propresenter_assets_path)
                                    
                                    # Update QR code element
                                    if elem.name == "qr_code" and link:
                                        # Use unique filename to avoid cache collisions
                                        qr_uuid = str(uuid_module.uuid4())[:8]
                                        qr_path = media_dir / f"qr_{qr_uuid}.png"
                                        generate_qr_image(link, qr_path)
                                        update_media_element(elem, qr_path, propresenter_assets_path)
            
            # Add the new cue to the presentation
            final_pres.cues.append(new_cue)
            
            # CRITICAL: Register the cue in cue_identifiers
            if len(final_pres.cue_groups) > 0:
                cue_id = final_pres.cue_groups[0].cue_identifiers.add()
                cue_id.string = new_cue.uuid.string
        
        # Fix all media paths (including template elements) to match production environment
        if propresenter_assets_path:
             fix_all_media_paths(final_pres, propresenter_assets_path)

        # Serialize and save
        output_data = final_pres.SerializeToString()
        
        if as_bundle:
            # Save .pro to working directory
            pro_name = output_path.stem + ".pro"
            if pro_name.endswith(".probundle.pro"):
                 pro_name = output_path.stem.replace(".probundle", "") + ".pro"
            
            # Usually bundles contain "presentation.pro" or the named file
            # Let's use the file stem
            temp_pro_path = work_dir / pro_name
            with open(temp_pro_path, 'wb') as f:
                f.write(output_data)
            
            # Zip it up - preserve Media/ folder structure
            # Match ProPresenter's format (DEFLATED with unicode filenames)
            print(f"   Zipping bundle to {output_path}...")
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(work_dir):
                    for file in files:
                        file_path = Path(root) / file
                        # Preserve relative path from work_dir, use forward slashes
                        arcname = str(file_path.relative_to(work_dir)).replace('\\', '/')
                        zipf.write(file_path, arcname)
                        
        else:
            # Standalone .pro
            with open(output_path, 'wb') as f:
                f.write(output_data)
                
            # Note: The images are still in temp dir and will be deleted!
            # If standalone, we should probably warn or move them.
            # But the user specifically asked for bundles to fix this.
            print(f"   [WARN] Standalone .pro generated, but images reference temp files: {work_dir}")

        print(f"   [OK] Generated {len(announcements)} slides")
        print(f"   [OK] Saved to: {output_path}")
        print(f"   [OK] File size: {len(output_data):,} bytes")
        
    except Exception as e:
        print(f"   [ERROR] Generation failed: {e}")
        raise
    finally:
        # Cleanup
        try:
            work_dir_obj.cleanup()
        except:
            pass


def main():
    """Test the generator with sample data."""
    test_announcements = [
        {
            "title": "Community Dinner",
            "body": "Join us for a wonderful evening of fellowship! We'll have great food, music, and time to connect with one another.",
            # Real test image URL (picsum is more accessible)
            "image_url": "https://picsum.photos/600/400",
            "link": "https://fumcwl.org/dinner"
        },
        {
            "title": "Youth Group Retreat",
            "body": "Our annual youth retreat is coming up! Sign up now to reserve your spot. Cost is $50 per person.",
            # Real test image URL
            "image_url": "https://picsum.photos/600/400",
            "link": "https://fumcwl.org/youth"
        },
    ]
    
    output_path = REPO_ROOT / "packages" / "announcements" / "output" / "test_announcements.probundle"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("ProPresenter Announcement Generator - Test Run (Bundle)")
    print("=" * 60)
    
    generate_pro_file(test_announcements, str(output_path), as_bundle=True)
    
    print("\n" + "=" * 60)
    print("[OK] Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
