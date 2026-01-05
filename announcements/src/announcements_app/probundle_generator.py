"""Generate ProPresenter .probundle files from announcement data."""
from __future__ import annotations

import os
import sys
import uuid
import base64
import zipfile
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any

import qrcode
import requests
from PIL import Image

# Add protobuf path
# Path hierarchy: probundle_generator.py -> announcements_app -> src -> announcements -> repo_root
_PROTO_PATH = Path(__file__).resolve().parents[3] / "slides" / "ProPresenter7_Proto" / "generated"
if str(_PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(_PROTO_PATH))

import presentation_pb2
import cue_pb2
import action_pb2
import slide_pb2
import graphicsData_pb2
import basicTypes_pb2
import background_pb2

from .settings import LOGO_PATH, BRAND_COLOR_1
from .summarize import summarize_text


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4()).upper()


def rgb_to_normalized(rgb_tuple: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert RGB (0-255) to normalized float (0.0-1.0)."""
    return (rgb_tuple[0]/255.0, rgb_tuple[1]/255.0, rgb_tuple[2]/255.0)


def create_uuid_message(uuid_str: str) -> basicTypes_pb2.UUID:
    """Create a UUID protobuf message."""
    u = basicTypes_pb2.UUID()
    u.string = uuid_str
    return u


def create_color(red: float, green: float, blue: float, alpha: float = 1.0) -> basicTypes_pb2.Color:
    """Create a Color protobuf message."""
    c = basicTypes_pb2.Color()
    c.red = red
    c.green = green
    c.blue = blue
    c.alpha = alpha
    return c


def generate_rtf_text(text: str, font_name: str = "SourceSansPro-Bold", 
                      font_size: int = 48, bold: bool = False, 
                      italic: bool = False, alignment: str = "left", 
                      color: tuple[float, float, float] = None) -> bytes:
    """
    Generate RTF formatted text and return as bytes.
    
    Args:
        text: Plain text content
        font_name: Font family name
        font_size: Font size in points
        bold: Whether text is bold
        italic: Whether text is italic
        alignment: Text alignment (left, center, right, justify)
        color: Tuple of (R, G, B) where each is 0.0-1.0 normalized float
    
    Returns:
        RTF bytes (not base64 encoded)
    """
    # RTF alignment codes
    align_codes = {
        "left": r"\ql",
        "center": r"\qc",
        "right": r"\qr",
        "justify": r"\qj"
    }
    align_code = align_codes.get(alignment, r"\ql")
    
    # Font style codes
    style = ""
    if bold:
        style += r"\b"
    if italic:
        style += r"\i"
    
    # Convert normalized color to 0-255 RGB if provided, otherwise use black
    if color:
        r_val = int(color[0] * 255)
        g_val = int(color[1] * 255)
        b_val = int(color[2] * 255)
        color_ref = 2  # Reference color index 2
        color_table = f"{{\\colortbl;\\red255\\green255\\blue255;\\red{r_val}\\green{g_val}\\blue{b_val};}}"
        expanded_color = f"{{\\*\\expandedcolortbl;;\\cssrgb\\c{int(color[0]*100000)}\\c{int(color[1]*100000)}\\c{int(color[2]*100000)}}}"
    else:
        color_ref = 2
        color_table = r"{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}"
        expanded_color = r"{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;}"
    
    # Escape special RTF characters
    text = text.replace("\\", "\\\\")
    text = text.replace("{", r"\{")
    text = text.replace("}", r"\}")
    text = text.replace("\n", r"\par ")
    
    # Build RTF document
    rtf = (
        r"{\rtf1\ansi\ansicpg1252\cocoartf2822"
        r"\cocoatextscaling0\cocoaplatform0"
        r"{\fonttbl\f0\fnil\fcharset0 " + font_name + r";}"
        + color_table +
        expanded_color +
        r"\deftab1680"
        r"\pard\pardeftab1680\pardirnatural" + align_code + r"\partightenfactor0"
        r"\f0" + style + r"\fs" + str(font_size * 2) + r" \cf" + str(color_ref) + r" \up0 " + text + r"}"
    )
    
    # Return as bytes
    return rtf.encode('utf-8')


def generate_qr_code(link: str, output_path: Path) -> bool:
    """Generate QR code and save to file."""
    try:
        qr = qrcode.QRCode(border=1, box_size=10)
        qr.add_data(link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(output_path))
        return True
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return False


def download_image(url: str, output_path: Path) -> tuple[bool, int, int]:
    """
    Download image from URL and save to file.
    
    Returns:
        Tuple of (success, width, height)
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        width, height = img.size
        
        # Convert to PNG if needed
        if img.format != 'PNG':
            img = img.convert('RGBA')
        
        img.save(str(output_path), 'PNG')
        return True, width, height
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return False, 0, 0


def create_media_element(media_uuid: str, file_path: str, width: int, height: int,
                         bounds_x: float, bounds_y: float, bounds_w: float, bounds_h: float,
                         element_uuid: str, element_name: str = "") -> Any:
    """Create a media (image) element."""
    
    element = graphicsData_pb2.Graphics.Element()
    element.uuid.CopyFrom(create_uuid_message(element_uuid))
    if element_name:
        element.name = element_name
    
    # Set bounds
    element.bounds.origin.x = bounds_x
    element.bounds.origin.y = bounds_y
    element.bounds.size.width = bounds_w
    element.bounds.size.height = bounds_h
    element.opacity = 1.0
    element.aspect_ratio_locked = True
    
    # Create path (rectangle)
    path = element.path
    path.closed = True
    path.shape.type = graphicsData_pb2.Graphics.Path.Shape.TYPE_RECTANGLE
    
    # Add rectangle points
    for px, py in [(0, 0), (1, 0), (1, 1), (0, 1)]:
        point = path.points.add()
        point.point.x = px
        point.point.y = py
        point.q0.x = px
        point.q0.y = py
        point.q1.x = px
        point.q1.y = py
    
    # Set fill with media
    element.fill.enable = True
    element.fill.media.uuid.CopyFrom(create_uuid_message(media_uuid))
    
    # Set URL
    element.fill.media.url.absolute_string = f"file://{file_path}"
    element.fill.media.url.platform = basicTypes_pb2.URL.Platform.PLATFORM_WIN32
    element.fill.media.url.local.root = basicTypes_pb2.URL.LocalRelativePath.Root.ROOT_SHOW
    element.fill.media.url.local.path = Path(file_path).name
    
    # Set metadata
    element.fill.media.metadata.format = "png"
    element.fill.media.image.drawing.natural_size.width = width
    element.fill.media.image.drawing.natural_size.height = height
    
    # Stroke
    element.stroke.width = 3.0
    element.stroke.color.CopyFrom(create_color(1.0, 1.0, 1.0, 1.0))
    
    # Shadow
    element.shadow.angle = 315.0
    element.shadow.offset = 5.0
    element.shadow.radius = 5.0
    element.shadow.color.CopyFrom(create_color(0.0, 0.0, 0.0, 1.0))
    element.shadow.opacity = 0.75
    
    # Feather
    element.feather.radius = 0.05
    
    return element


def create_text_element(text: str, element_uuid: str, element_name: str,
                        bounds_x: float, bounds_y: float, bounds_w: float, bounds_h: float,
                        font_name: str, font_size: int, bold: bool = False, italic: bool = False,
                        alignment: str = "left", bg_color: tuple = None, text_color: tuple = None) -> Any:
    """Create a text element with RTF content.
    
    Args:
        text_color: Tuple of (R, G, B) where each is 0.0-1.0 normalized float
    """
    
    element = graphicsData_pb2.Graphics.Element()
    element.uuid.CopyFrom(create_uuid_message(element_uuid))
    element.name = element_name
    
    # Set bounds
    element.bounds.origin.x = bounds_x
    element.bounds.origin.y = bounds_y
    element.bounds.size.width = bounds_w
    element.bounds.size.height = bounds_h
    element.opacity = 1.0
    
    # Create path (rectangle)
    path = element.path
    path.closed = True
    path.shape.type = graphicsData_pb2.Graphics.Path.Shape.TYPE_RECTANGLE
    
    # Add rectangle points
    for px, py in [(0, 0), (1, 0), (1, 1), (0, 1)]:
        point = path.points.add()
        point.point.x = px
        point.point.y = py
        point.q0.x = px
        point.q0.y = py
        point.q1.x = px
        point.q1.y = py
    
    # Background fill
    if bg_color:
        element.fill.color.CopyFrom(create_color(*bg_color, 1.0))
    
    # Stroke
    element.stroke.width = 3.0
    element.stroke.color.CopyFrom(create_color(1.0, 1.0, 1.0, 1.0))
    
    # Shadow
    element.shadow.angle = 315.0
    element.shadow.offset = 5.0
    element.shadow.radius = 5.0
    element.shadow.color.CopyFrom(create_color(0.0, 0.0, 0.0, 1.0))
    element.shadow.opacity = 0.75
    
    # Feather
    element.feather.radius = 0.05
    
    # Text attributes
    element.text.attributes.font.name = font_name
    element.text.attributes.font.size = float(font_size)
    if bold:
        element.text.attributes.font.bold = True
    if italic:
        element.text.attributes.font.italic = True
    element.text.attributes.font.family = "Source Sans Pro"
    
    # Text color (use provided color or default to black)
    if text_color:
        element.text.attributes.text_solid_fill.CopyFrom(create_color(text_color[0], text_color[1], text_color[2], 1.0))
    else:
        element.text.attributes.text_solid_fill.CopyFrom(create_color(0.0, 0.0, 0.0, 1.0))
    
    # Paragraph alignment
    align_map = {
        "left": graphicsData_pb2.Graphics.Text.Attributes.Paragraph.ALIGNMENT_LEFT,
        "center": graphicsData_pb2.Graphics.Text.Attributes.Paragraph.ALIGNMENT_CENTER,
        "right": graphicsData_pb2.Graphics.Text.Attributes.Paragraph.ALIGNMENT_RIGHT,
    }
    element.text.attributes.paragraph_style.alignment = align_map.get(alignment, 
        graphicsData_pb2.Graphics.Text.Attributes.Paragraph.ALIGNMENT_LEFT)
    element.text.attributes.paragraph_style.line_height_multiple = 1.0
    element.text.attributes.paragraph_style.default_tab_interval = 84.0
    
    # Generate and set RTF data
    element.text.rtf_data = generate_rtf_text(text, font_name, font_size, bold, italic, alignment, color=text_color)
    
    # Vertical alignment
    element.text.vertical_alignment = graphicsData_pb2.Graphics.Text.VERTICAL_ALIGNMENT_MIDDLE
    element.text.is_superscript_standardized = True
    
    # Shadow for text
    element.text.shadow.angle = 315.0
    element.text.shadow.offset = 5.0
    element.text.shadow.radius = 5.0
    element.text.shadow.color.CopyFrom(create_color(0.0, 0.0, 0.0, 1.0))
    element.text.shadow.opacity = 0.75
    
    return element


def create_announcement_slide(announcement: dict, slide_index: int, 
                              media_dir: Path, template_slide: Any) -> tuple[Any, list]:
    """
    Create a slide for an announcement.
    
    Returns:
        Tuple of (slide_proto, list of media files to include)
    """
    import presentationSlide_pb2
    
    media_files = []
    
    # Create new slide by copying template structure
    slide = presentationSlide_pb2.PresentationSlide()
    slide.CopyFrom(template_slide)
    
    # Clear existing elements and rebuild with announcement data
    del slide.base_slide.elements[:]
    
    # 1. Title element (always present)
    brand_color_normalized = rgb_to_normalized(BRAND_COLOR_1)
    title_element = create_text_element(
        text=announcement["title"],
        element_uuid=generate_uuid(),
        element_name="title_text",
        bounds_x=50,
        bounds_y=0.0,
        bounds_w=1820,
        bounds_h=275,
        font_name="SourceSansPro-Black",
        font_size=84,
        bold=True,
        alignment="left",
        bg_color=(0.11764706, 0.5647059, 1.0),
        text_color=brand_color_normalized
    )
    # Change stroke color to primary brand color
    title_element.stroke.color.CopyFrom(create_color(*brand_color_normalized, 1.0))
    slide_element = slide.base_slide.elements.add()
    slide_element.element.CopyFrom(title_element)
    slide_element.info = 3
    
    # 2. Body element (always present)
    body_text = announcement.get("body", "")
    # Summarize body text to fit in the box
    if body_text:
        body_text = summarize_text(body_text)
    
    body_element = create_text_element(
        text=body_text,
        element_uuid=generate_uuid(),
        element_name="body_text",
        bounds_x=50,
        bounds_y=265,
        bounds_w=1150,
        bounds_h=375,
        font_name="SourceSansPro-Black",
        font_size=50,
        alignment="left",
        bg_color=(0.13, 0.59, 0.95)
    )
    slide_element = slide.base_slide.elements.add()
    slide_element.element.CopyFrom(body_element)
    slide_element.info = 2
    
    # 3. Logo (always present)
    logo_path = LOGO_PATH
    if os.path.exists(logo_path):
        # Copy logo to media dir
        logo_dest = media_dir / "logo.png"
        if not logo_dest.exists():
            import shutil
            shutil.copy(logo_path, logo_dest)
            media_files.append(("logo.png", logo_dest))
        
        with Image.open(logo_path) as img:
            logo_w, logo_h = img.size
        
        logo_element = create_media_element(
            media_uuid=generate_uuid(),
            file_path=f"Media/Assets/logo.png",
            width=logo_w,
            height=logo_h,
            bounds_x=0.0,
            bounds_y=863.98,
            bounds_w=728.84,
            bounds_h=216.02,
            element_uuid=generate_uuid(),
            element_name="logo"
        )
        slide_element = slide.base_slide.elements.add()
        slide_element.element.CopyFrom(logo_element)
    
    # 4. Main image (if exists)
    if announcement.get("image_url"):
        img_filename = f"announcement_{slide_index + 1}_image.png"
        img_path = media_dir / img_filename
        
        success, img_w, img_h = download_image(announcement["image_url"], img_path)
        if success:
            media_files.append((f"Media/Assets/{img_filename}", img_path))
            
            image_element = create_media_element(
                media_uuid=generate_uuid(),
                file_path=f"Media/Assets/{img_filename}",
                width=img_w,
                height=img_h,
                bounds_x=1250,
                bounds_y=275,
                bounds_w=620,
                bounds_h=755,
                element_uuid=generate_uuid(),
                element_name="image"
            )
            slide_element = slide.base_slide.elements.add()
            slide_element.element.CopyFrom(image_element)
    
    # 5. QR Code (if link exists)
    if announcement.get("link"):
        qr_filename = f"announcement_{slide_index + 1}_qr.png"
        qr_path = media_dir / qr_filename
        
        if generate_qr_code(announcement["link"], qr_path):
            media_files.append((f"Media/Assets/{qr_filename}", qr_path))
            
            # Get QR code size
            with Image.open(qr_path) as img:
                qr_w, qr_h = img.size
            
            qr_element = create_media_element(
                media_uuid=generate_uuid(),
                file_path=f"Media/Assets/{qr_filename}",
                width=qr_w,
                height=qr_h,
                bounds_x=781.32,
                bounds_y=619.2,
                bounds_w=395.0,
                bounds_h=395.0,
                element_uuid=generate_uuid(),
                element_name="qr_code"
            )
            slide_element = slide.base_slide.elements.add()
            slide_element.element.CopyFrom(qr_element)
            
            # 6. QR text (button text)
            qr_text = announcement.get("button_text", "Scan for more info")
            qr_text_element = create_text_element(
                text=qr_text,
                element_uuid=generate_uuid(),
                element_name="qr_text",
                bounds_x=710.02,
                bounds_y=1014.2,
                bounds_w=537.6,
                bounds_h=39.04,
                font_name="SourceSansPro-It",
                font_size=32,
                italic=True,
                alignment="center",
                bg_color=(0.13, 0.59, 0.95)
            )
            slide_element = slide.base_slide.elements.add()
            slide_element.element.CopyFrom(qr_text_element)
            slide_element.info = 2
    
    return slide, media_files


def create_probundle(announcements: list[dict], output_path: Path) -> None:
    """
    Create a .probundle file with all announcements.
    
    Args:
        announcements: List of announcement dictionaries
        output_path: Path where the .probundle file should be saved
    """
    # Create temp directory for media
    media_dir = output_path.parent / "temp_media"
    media_dir.mkdir(exist_ok=True, parents=True)
    
    # Load template presentation
    template_path = Path(__file__).resolve().parents[3] / "slides" / "templates" / "announcement_template_extracted" / "announcement_template.pro"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    
    # Read template
    with open(template_path, 'rb') as f:
        template_data = f.read()
    
    template_pres = presentation_pb2.Presentation()
    template_pres.ParseFromString(template_data)
    
    # Get template slide
    if not template_pres.cues or not template_pres.cues[0].actions:
        raise ValueError("Template presentation has no slides")
    
    template_slide = template_pres.cues[0].actions[0].slide.presentation
    
    # Create new presentation
    presentation = presentation_pb2.Presentation()
    presentation.CopyFrom(template_pres)
    
    # Clear existing cues
    del presentation.cues[:]
    del presentation.cue_groups[:]
    
    # Create cue group
    cue_group = presentation.cue_groups.add()
    cue_group.group.uuid.CopyFrom(create_uuid_message(generate_uuid()))
    
    # Collect all media files
    all_media_files = []
    
    # Create slides for each announcement
    for idx, announcement in enumerate(announcements):
        print(f"Creating slide {idx + 1}/{len(announcements)}: {announcement['title'][:50]}...")
        
        slide, media_files = create_announcement_slide(
            announcement, idx, media_dir, template_slide
        )
        all_media_files.extend(media_files)
        
        # Create cue
        cue = presentation.cues.add()
        cue_uuid = generate_uuid()
        cue.uuid.CopyFrom(create_uuid_message(cue_uuid))
        # cue.completion_action_type = cue_pb2.Cue.COMPLETION_ACTION_TYPE_LAST  # Use default
        
        # Add to cue group
        cue_identifier = cue_group.cue_identifiers.add()
        cue_identifier.string = cue_uuid
        
        # Create action
        action = cue.actions.add()
        action.uuid.CopyFrom(create_uuid_message(generate_uuid()))
        # action.is_enabled = True  # Use default
        action.type = action_pb2.Action.ACTION_TYPE_PRESENTATION_SLIDE
        action.slide.presentation.CopyFrom(slide)
    
    # Update presentation name
    presentation.name = f"announcements_{output_path.stem}"
    presentation.uuid.CopyFrom(create_uuid_message(generate_uuid()))
    
    # Serialize presentation
    presentation_data = presentation.SerializeToString()
    
    # Create .probundle (ZIP file)
    print(f"Creating .probundle file: {output_path}")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zipf:
        # Add presentation file
        zipf.writestr(f"{output_path.stem}.pro", presentation_data)
        
        # Add all media files
        for zip_path, file_path in all_media_files:
            if file_path.exists():
                zipf.write(file_path, zip_path)
    
    # Cleanup temp media
    shutil.rmtree(media_dir, ignore_errors=True)
    
    print(f"✓ Created {output_path}")
    print(f"  - {len(announcements)} announcements")
    print(f"  - {len(all_media_files)} media files")
