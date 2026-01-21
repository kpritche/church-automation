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
# Use the extracted template directory
ANNOUNCEMENT_TEMPLATE = TEMPLATE_DIR / "announcement_template" / "announcement_template.pro"
# Media assets from the template bundle
TEMPLATE_MEDIA_DIR = TEMPLATE_DIR / "announcement_template" / "Users" / "fcproduction" / "Documents" / "ProPresenter" / "Media" / "Assets"


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
    """Load a .pro template file or extract from .probundle (ZIP or 7z)."""
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    
    pres = presentation_pb2.Presentation()
    
    # Handle .probundle (can be ZIP or 7z format)
    if path.suffix.lower() in ['.probundle', '.zip', '.7z']:
        import zipfile
        import tempfile
        
        # Try ZIP format first
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(path, 'r') as z:
                    # Find the .pro file in the bundle
                    pro_files = [name for name in z.namelist() if name.endswith('.pro')]
                    if not pro_files:
                        raise ValueError(f"No .pro file found in bundle: {path}")
                    
                    # Use the first .pro file found
                    pro_name = pro_files[0]
                    temp_pro = Path(temp_dir) / "template.pro"
                    
                    with z.open(pro_name) as src:
                        with open(temp_pro, 'wb') as dst:
                            dst.write(src.read())
                    
                    with open(temp_pro, 'rb') as f:
                        pres.ParseFromString(f.read())
        except zipfile.BadZipFile:
            # Try 7z format
            try:
                import py7zr
                with tempfile.TemporaryDirectory() as temp_dir:
                    with py7zr.SevenZipFile(path, 'r') as z:
                        z.extractall(temp_dir)
                    
                    # Find .pro file
                    pro_files = list(Path(temp_dir).rglob('*.pro'))
                    if not pro_files:
                        raise ValueError(f"No .pro file found in bundle: {path}")
                    
                    with open(pro_files[0], 'rb') as f:
                        pres.ParseFromString(f.read())
            except Exception as e:
                raise ValueError(f"Failed to extract bundle {path}: {e}")
    else:
        # Regular .pro file
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


def find_element_by_rtf_content(elements, search_text: str):
    """Find an element wrapper by searching for text in its rtf_data.
    
    Fallback method when element.name is not set but rtf_data contains placeholder text.
    """
    for elem_wrapper in elements:
        if elem_wrapper.HasField('element'):
            elem = elem_wrapper.element
            if elem.HasField('text') and elem.text.rtf_data:
                try:
                    rtf_str = elem.text.rtf_data.decode('utf-8', errors='ignore')
                    if search_text in rtf_str:
                        return elem_wrapper
                except:
                    continue
    return None


def update_media_element(element, image_path: Path, propresenter_assets_path: str = None) -> None:
    """Update a media element's URL to point to a local image.
    
    Args:
        element: The protobuf element to update
        image_path: Path to the image file
        propresenter_assets_path: The ProPresenter Media/Assets path for absolute_string
    """
    try:
        import basicTypes_pb2
        from PIL import Image
        
        if not element.HasField('fill') or not element.fill.HasField('media'):
            print(f"      [WARN] Element does not have media fill")
            return
            
        media = element.fill.media
        media.uuid.string = str(uuid_module.uuid4()).upper()
        
        # Set platform to macOS (user enforced)
        media.url.platform = basicTypes_pb2.URL.PLATFORM_MACOS
        
        if propresenter_assets_path:
            # For bundles: Don't use absolute paths - use relative paths only
            # ProPresenter will look in the bundle's Media/Assets folder first
            
            # CLEAR absolute_string so ProPresenter uses the bundle-relative path
            media.url.ClearField('absolute_string')
            
            # Set local path relative to the bundle root
            media.url.local.root = basicTypes_pb2.URL.LocalRelativePath.ROOT_SHOW
            media.url.local.path = f"Media/Assets/{image_path.name}"
            
            print(f"         [DEBUG] Set media path to: Media/Assets/{image_path.name}")
            print(f"         [DEBUG] Cleared absolute_string")
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
            print(f"      [WARN] Could not read image dimensions for {image_path.name}: {e}")
            
    except Exception as e:
        print(f"      [ERROR] Failed to update media element: {e}")
        import traceback
        traceback.print_exc()


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


def generate_rtf_text(text: str, font_name: str = "SourceSansPro-Regular", 
                     font_size: int = 48, bold: bool = False, 
                     italic: bool = False, color: tuple = None) -> bytes:
    """Generate RTF data for given text with formatting.
    
    Args:
        text: Plain text to convert to RTF
        font_name: Font name (e.g., 'SourceSansPro-Black')
        font_size: Font size in points
        bold: Whether text is bold
        italic: Whether text is italic
        color: RGB tuple (0-255) for text color
    
    Returns:
        Base64-encoded RTF bytes
    """
    import base64
    
    # Escape the text for RTF
    escaped = _rtf_escape_text(text)
    
    # Build RTF header
    rtf = r'{\rtf1\ansi\ansicpg1252\cocoartf2822' + '\n'
    rtf += r'{\fonttbl\f0\fnil\fcharset0 ' + font_name + ';}'  + '\n'
    
    # Color table (black text by default)
    if color:
        r, g, b = color
        rtf += r'{\colortbl;\red' + str(r) + r'\green' + str(g) + r'\blue' + str(b) + ';}'  + '\n'
    else:
        rtf += r'{\colortbl;\red0\green0\blue0;}'  + '\n'
    
    rtf += r'{\*\expandedcolortbl;;}'  + '\n'
    rtf += r'\deftab720\pardefftab720\pardirnatural\partightenfactor0'  + '\n\n'
    
    # Font formatting
    rtf += r'\f0'
    if bold:
        rtf += r'\b'
    if italic:
        rtf += r'\i'
    rtf += r'\fs' + str(font_size * 2)  # RTF uses half-points
    rtf += ' ' + escaped
    rtf += '}'  # Close RTF
    
    # Return as base64-encoded bytes
    return base64.b64encode(rtf.encode('utf-8'))


def generate_pro_file(announcements: List[dict], output_path: str, as_bundle: bool = False) -> None:
    """Generate a ProPresenter file (.pro or .probundle).
    
    Args:
        announcements: List of announcement data
        output_path: Destination path
        as_bundle: If True, creates a .probundle (zip) with assets
    """
    output_path = Path(output_path)
    print(f"   Loading template...")
    print(f"      Announcement: {ANNOUNCEMENT_TEMPLATE}")
    
    # Load announcement template
    announcement_pres = load_template(ANNOUNCEMENT_TEMPLATE)
    
    # Start with a deep copy of the announcement template (preserves transition, guidelines, etc.)
    final_pres = deepcopy(announcement_pres)
    
    # Generate new UUID for the presentation and cue group
    final_pres.uuid.string = str(uuid_module.uuid4()).upper()
    final_pres.name = "Weekly Announcements"
    
    if len(final_pres.cue_groups) > 0:
        final_pres.cue_groups[0].group.uuid.string = str(uuid_module.uuid4()).upper()
    
    # Get the announcement template's first cue as our slide template
    if len(announcement_pres.cues) == 0:
        raise ValueError("Announcement template has no cues/slides")
    template_cue = announcement_pres.cues[0]
    
    # Clear existing cues - we'll add new ones for each announcement
    del final_pres.cues[:]
    if len(final_pres.cue_groups) > 0:
        del final_pres.cue_groups[0].cue_identifiers[:]
    
    # Working directory (temp)
    # If bundling, we need a persistent structure to zip
    work_dir_obj = tempfile.TemporaryDirectory(prefix="propresenter_")
    work_dir = Path(work_dir_obj.name)
    print(f"   Working directory: {work_dir}")
    
    try:
        # For bundles, create Media subdirectory matching ProPresenter's structure
        if as_bundle:
            media_dir = work_dir / "Media" / "Assets"
            media_dir.mkdir(parents=True, exist_ok=True)
            # ProPresenter expects absolute path to its Media/Assets folder
            # User specified production path on Mac
            propresenter_assets_path = "file:///Users/fcproduction/Documents/ProPresenter/Media/Assets"
            
            # Extract static template assets from template bundle if available
            # Only copy logo and other static assets - skip placeholder images that will be replaced
            if TEMPLATE_MEDIA_DIR.exists() and TEMPLATE_MEDIA_DIR.is_dir():
                print(f"   Copying template assets from {TEMPLATE_MEDIA_DIR.name}...")
                for asset_file in TEMPLATE_MEDIA_DIR.glob('*.*'):
                    # Skip UUID-named placeholder files - these will be replaced with dynamic content
                    if len(asset_file.stem) == 36 and '-' in asset_file.stem:  # UUID format
                        print(f"      Skipped placeholder: {asset_file.name}")
                        continue
                    
                    dest_path = media_dir / asset_file.name
                    # Don't overwrite if file already exists (dynamic content takes priority)
                    if not dest_path.exists():
                        shutil.copy2(asset_file, dest_path)
                        print(f"      Copied: {asset_file.name}")
                print(f"   Template assets copied to {media_dir}")
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
            
            # Regenerate UUIDs for ALL actions (not just first)
            for action in new_cue.actions:
                action.uuid.string = str(uuid_module.uuid4()).upper()
                
                if action.HasField('slide'):
                    slide_action = action.slide
                    
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
                        
                        # Regenerate UUIDs for template_guidelines
                        for guideline in pres_slide.template_guidelines:
                            if guideline.HasField('uuid'):
                                guideline.uuid.string = str(uuid_module.uuid4()).upper()
            
            # Now update elements by name
            # Get the base_slide elements for targeted updates
            base_slide_elements = None
            for action in new_cue.actions:
                if action.HasField('slide') and action.slide.HasField('presentation'):
                    if action.slide.presentation.HasField('base_slide'):
                        base_slide_elements = action.slide.presentation.base_slide.elements
                        break
            
            if base_slide_elements:
                # Update title text by element name
                title_elem = find_element_by_name(base_slide_elements, 'title_text')
                if title_elem and title_elem.HasField('element') and title_elem.element.HasField('text'):
                    title_elem.element.text.rtf_data = generate_rtf_text(
                        title, font_name="SourceSansPro-Black", font_size=84, bold=True
                    )
                    print(f"      → Updated title text element")
                
                # Update body text by element name (with rtf_data fallback)
                body_elem = find_element_by_name(base_slide_elements, 'body_text')
                if not body_elem:
                    # Fallback: search for "body_text" in rtf_data
                    body_elem = find_element_by_rtf_content(base_slide_elements, 'body_text')
                
                if body_elem and body_elem.HasField('element') and body_elem.element.HasField('text'):
                    body_elem.element.text.rtf_data = generate_rtf_text(
                        body, font_name="SourceSansPro-Regular", font_size=48
                    )
                    print(f"      → Updated body text element")
                
                # Update QR code by element name if link present
                if link:
                    qr_elem = find_element_by_name(base_slide_elements, 'qr_code')
                    if qr_elem and qr_elem.HasField('element'):
                        qr_uuid = str(uuid_module.uuid4())[:8]
                        qr_path = media_dir / f"qr_{qr_uuid}.png"
                        generate_qr_image(link, qr_path)
                        update_media_element(qr_elem.element, qr_path, propresenter_assets_path)
                        print(f"      → Updated QR code: {qr_path.name}")
                
                # Update announcement image by element name if URL present
                if image_url:
                    img_elem = find_element_by_name(base_slide_elements, 'announcement_image')
                    if img_elem and img_elem.HasField('element'):
                        local_img = download_image(image_url, media_dir)
                        if local_img:
                            update_media_element(img_elem.element, local_img, propresenter_assets_path)
                            print(f"      → Updated image: {local_img.name}")
            
            # Add the new cue to the presentation
            final_pres.cues.append(new_cue)
            
            # CRITICAL: Register the cue in cue_identifiers
            if len(final_pres.cue_groups) > 0:
                cue_id = final_pres.cue_groups[0].cue_identifiers.add()
                cue_id.string = new_cue.uuid.string
        
        # Don't call fix_all_media_paths for bundles - we want relative paths only
        # The absolute paths prevent Mac from finding media in the bundle
        # if propresenter_assets_path:
        #      fix_all_media_paths(final_pres, propresenter_assets_path)

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
            print(f"   Zipping bundle to {output_path}...")
            media_file_count = len(list(media_dir.glob('*.*'))) if media_dir.exists() else 0
            print(f"   Media files to include: {media_file_count}")
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(work_dir):
                    for file in files:
                        file_path = Path(root) / file
                        # Preserve relative path from work_dir
                        arcname = str(file_path.relative_to(work_dir))
                        zipf.write(file_path, arcname)
                        
            print(f"   Bundle contents:")
            with zipfile.ZipFile(output_path, 'r') as zipf:
                for name in sorted(zipf.namelist()):
                    print(f"      - {name}")
                        
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
