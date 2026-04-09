"""Automated bulletin cover generation from UMC Discipleship resources."""
from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple
import re
import io
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


REQUEST_TIMEOUT = 30


@dataclass
class CoverWeekInfo:
    """Information about a specific worship week for cover generation."""
    liturgical_name: str
    image_url: str


def _parse_date_from_string(date_str: str) -> Optional[date]:
    """Parse a date string like 'APRIL 12, 2026' into a date object."""
    try:
        # Format: "MONTH DAY, YEAR"
        match = re.search(r'([A-Z]+)\s+(\d+),\s+(\d{4})', date_str.upper())
        if match:
            month_str, day_str, year_str = match.groups()
            months = {
                'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4,
                'MAY': 5, 'JUNE': 6, 'JULY': 7, 'AUGUST': 8,
                'SEPTEMBER': 9, 'OCTOBER': 10, 'NOVEMBER': 11, 'DECEMBER': 12
            }
            if month_str in months:
                return date(int(year_str), months[month_str], int(day_str))
    except (ValueError, AttributeError):
        pass
    return None


def scrape_week_info(service_date: date) -> CoverWeekInfo:
    """
    Scrape the UMC Discipleship lectionary page to find the worship week info.
    
    Args:
        service_date: The date of the Sunday service
        
    Returns:
        CoverWeekInfo with liturgical name and bulletin image URL
        
    Raises:
        ValueError: If no entry is found for the given date
        requests.RequestException: If network request fails
    """
    # Fetch the lectionary index page for the service year
    year = service_date.year
    lectionary_url = f"https://www.umcdiscipleship.org/content-library/lectionary/{year}"
    
    print(f"[cover_generator] Fetching lectionary page: {lectionary_url}")
    response = requests.get(lectionary_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all text nodes that might contain date entries
    # Pattern: "MONTH DAY, YEAR LITURGICAL NAME"
    # Followed by an <a> tag with the week planning URL
    
    week_url: Optional[str] = None
    liturgical_name: Optional[str] = None
    
    # Search for date patterns in the page text
    text_content = soup.get_text()
    lines = text_content.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        parsed_date = _parse_date_from_string(line)
        
        if parsed_date == service_date:
            # Found the matching date line
            # Extract liturgical name from this line (everything after the date)
            date_match = re.search(r'([A-Z]+\s+\d+,\s+\d{4})\s+(.*)', line.upper())
            if date_match:
                liturgical_name = date_match.group(2).strip()
            
            # Find the next <a> tag with an href (the week planning URL)
            # Look in the raw HTML near this text
            for link in soup.find_all('a', href=True):
                link_text = link.get_text().strip()
                # The link should be near this date
                if link.parent and parsed_date:
                    parent_text = link.parent.get_text()
                    if _parse_date_from_string(parent_text) == parsed_date:
                        week_url = link['href']
                        break
            
            if week_url:
                break
    
    if not week_url or not liturgical_name:
        raise ValueError(
            f"No lectionary entry found for {service_date.strftime('%B %d, %Y')}. "
            f"Found week_url={week_url}, liturgical_name={liturgical_name}"
        )
    
    # Derive the graphics page URL
    # Strip -lectionary-planning-notes suffix if present, then append -graphics
    graphics_url = week_url.rstrip('/')
    if graphics_url.endswith('-lectionary-planning-notes'):
        graphics_url = graphics_url[:-len('-lectionary-planning-notes')]
    graphics_url += '-graphics'
    
    print(f"[cover_generator] Fetching graphics page: {graphics_url}")
    graphics_response = requests.get(graphics_url, timeout=REQUEST_TIMEOUT)
    graphics_response.raise_for_status()
    
    graphics_soup = BeautifulSoup(graphics_response.text, 'html.parser')
    
    # Find the bulletin download link
    # Look for text containing "BULLETIN" followed by a download link
    bulletin_url: Optional[str] = None
    
    for element in graphics_soup.find_all(string=re.compile(r'BULLETIN', re.IGNORECASE)):
        # Find the next <a> tag with "Download" text
        parent = element.parent
        if parent:
            # Look for a link in the parent or nearby siblings
            for link in parent.find_all('a', href=True):
                if 'download' in link.get_text().lower() or link['href'].endswith(('.jpg', '.jpeg', '.png')):
                    bulletin_url = link['href']
                    break
            
            # Also check next siblings
            if not bulletin_url:
                next_sibling = parent.find_next_sibling()
                while next_sibling and not bulletin_url:
                    for link in next_sibling.find_all('a', href=True):
                        if 'download' in link.get_text().lower() or link['href'].endswith(('.jpg', '.jpeg', '.png')):
                            bulletin_url = link['href']
                            break
                    next_sibling = next_sibling.find_next_sibling()
        
        if bulletin_url:
            break
    
    if not bulletin_url:
        raise ValueError(f"Could not find bulletin image download link on {graphics_url}")
    
    print(f"[cover_generator] Found bulletin image: {bulletin_url}")
    
    return CoverWeekInfo(
        liturgical_name=liturgical_name,
        image_url=bulletin_url
    )


def download_bulletin_image(image_url: str) -> Image.Image:
    """
    Download a bulletin image from a URL.
    
    Args:
        image_url: URL to the bulletin image
        
    Returns:
        PIL Image object in RGB mode
        
    Raises:
        requests.RequestException: If download fails
        PIL.UnidentifiedImageError: If the content is not a valid image
    """
    print(f"[cover_generator] Downloading image from: {image_url}")
    response = requests.get(image_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    
    img = Image.open(io.BytesIO(response.content)).convert('RGB')
    print(f"[cover_generator] Image downloaded: {img.size[0]}x{img.size[1]}px")
    
    return img


# Phase 2: Color Analysis Functions


def wcag_contrast_ratio(color: Tuple[int, int, int]) -> float:
    """
    Calculate the WCAG contrast ratio of a color against white text.
    
    Args:
        color: RGB color tuple (0-255 for each channel)
        
    Returns:
        Contrast ratio value (1.0 = no contrast, 21.0 = maximum contrast)
    """
    # Calculate relative luminance using WCAG formula
    def relative_luminance(rgb: Tuple[int, int, int]) -> float:
        # Convert to 0-1 range
        r, g, b = [c / 255.0 for c in rgb]
        
        # Apply gamma correction
        def adjust(channel: float) -> float:
            if channel <= 0.03928:
                return channel / 12.92
            else:
                return ((channel + 0.055) / 1.055) ** 2.4
        
        r_adj = adjust(r)
        g_adj = adjust(g)
        b_adj = adjust(b)
        
        # Calculate luminance (formula from WCAG 2.0)
        return 0.2126 * r_adj + 0.7152 * g_adj + 0.0722 * b_adj
    
    # Calculate contrast ratio against white (luminance = 1.0)
    color_luminance = relative_luminance(color)
    white_luminance = 1.0
    
    # WCAG contrast ratio formula
    if white_luminance > color_luminance:
        ratio = (white_luminance + 0.05) / (color_luminance + 0.05)
    else:
        ratio = (color_luminance + 0.05) / (white_luminance + 0.05)
    
    return ratio


def is_full_bleed(image: Image.Image, page_w: float, page_h: float) -> bool:
    """
    Determine if an image aspect ratio matches the page aspect ratio (full bleed).
    
    Args:
        image: PIL Image to check
        page_w: Page width in points
        page_h: Page height in points
        
    Returns:
        True if image aspect ratio matches page within 5% tolerance
    """
    img_w, img_h = image.size
    img_aspect = img_w / img_h
    page_aspect = page_w / page_h
    
    # Allow 5% tolerance
    tolerance = 0.05
    return abs(img_aspect - page_aspect) < tolerance


def extract_fill_color(image: Image.Image) -> Tuple[int, int, int]:
    """
    Extract a suitable background fill color from the image palette.
    
    Selects a color that:
    - Is present in the image's color palette
    - Provides good contrast (WCAG AA: ≥4.5:1) with white text
    - Prefers darker colors
    
    Falls back to church primary color (22, 70, 62) if no suitable color found.
    
    Args:
        image: PIL Image to analyze
        
    Returns:
        RGB color tuple (0-255 for each channel)
    """
    CHURCH_PRIMARY_COLOR = (22, 70, 62)  # #16463E
    MIN_CONTRAST = 4.5  # WCAG AA standard
    
    try:
        # Quantize image to extract dominant colors
        quantized = image.quantize(colors=10)
        palette = quantized.getpalette()
        
        if not palette:
            return CHURCH_PRIMARY_COLOR
        
        # Extract RGB colors from palette
        colors = []
        for i in range(0, min(30, len(palette)), 3):
            if i + 2 < len(palette):
                color = (palette[i], palette[i + 1], palette[i + 2])
                colors.append(color)
        
        # Find the darkest color with sufficient contrast
        best_color = None
        best_luminance = 1.0  # Start with maximum (lightest)
        
        for color in colors:
            contrast = wcag_contrast_ratio(color)
            
            if contrast >= MIN_CONTRAST:
                # Calculate perceived luminance (simple approximation)
                luminance = (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255.0
                
                # Prefer darker colors (lower luminance)
                if luminance < best_luminance:
                    best_luminance = luminance
                    best_color = color
        
        if best_color:
            print(f"[cover_generator] Selected fill color: RGB{best_color} (contrast: {wcag_contrast_ratio(best_color):.1f}:1)")
            return best_color
        else:
            print(f"[cover_generator] No suitable palette color found, using church primary color")
            return CHURCH_PRIMARY_COLOR
    
    except Exception as exc:
        print(f"[cover_generator] Error extracting fill color: {exc}, using church primary color")
        return CHURCH_PRIMARY_COLOR


# Phase 3: Cover Page Renderer


def generate_branded_cover_pdf(
    image: Image.Image,
    service_name: str,
    liturgical_name: str,
    service_date_str: str,
    fill_color: Tuple[int, int, int]
) -> bytes:
    """
    Generate a branded bulletin cover page as a PDF.
    
    Args:
        image: Background image for the cover
        service_name: Name of the service (e.g., "Celebrate", "First Up")
        liturgical_name: Liturgical calendar name (e.g., "Second Sunday of Easter, Year A")
        service_date_str: Formatted date string (e.g., "April 12, 2026")
        fill_color: RGB color for background fill (behind image if not full-bleed)
        
    Returns:
        PDF bytes for the cover page
    """
    # Import paths
    try:
        from church_automation_shared.paths import FONTS_DIR, BULLETINS_DIR
        logo_path = BULLETINS_DIR / "bulletins_app" / "firstchurch_white_logo.png"
    except ImportError:
        # Fallback for running tests without full package installation
        bulletins_dir = Path(__file__).resolve().parent.parent
        logo_path = bulletins_dir / "bulletins_app" / "firstchurch_white_logo.png"
        fonts_dir = Path(__file__).resolve().parents[4] / "assets" / "fonts"
        FONTS_DIR = fonts_dir
    
    # Page constants
    PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 points
    
    # Register fonts (Source Sans Pro)
    fonts_available = True
    try:
        font_regular = FONTS_DIR / "SourceSansPro-Regular.ttf"
        font_bold = FONTS_DIR / "SourceSansPro-Bold.ttf"
        font_semibold = FONTS_DIR / "SourceSansPro-Semibold.ttf"  # Note: lowercase 'b'
        
        if 'SourceSansPro' not in pdfmetrics.getRegisteredFontNames():
            if font_regular.exists():
                pdfmetrics.registerFont(TTFont('SourceSansPro', str(font_regular)))
        if 'SourceSansPro-Bold' not in pdfmetrics.getRegisteredFontNames():
            if font_bold.exists():
                pdfmetrics.registerFont(TTFont('SourceSansPro-Bold', str(font_bold)))
        if 'SourceSansPro-Semibold' not in pdfmetrics.getRegisteredFontNames():
            if font_semibold.exists():
                pdfmetrics.registerFont(TTFont('SourceSansPro-Semibold', str(font_semibold)))
    except Exception as exc:
        print(f"[cover_generator] Warning: Could not register fonts: {exc}")
        fonts_available = False
    
    # Create PDF canvas
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    
    # Fill background with fill_color
    r, g, b = fill_color
    canvas.setFillColorRGB(r / 255.0, g / 255.0, b / 255.0)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    
    # Draw image (centered, scaled to fit)
    img_w, img_h = image.size
    scale = min(PAGE_WIDTH / img_w, PAGE_HEIGHT / img_h)
    draw_w = img_w * scale
    draw_h = img_h * scale
    x = (PAGE_WIDTH - draw_w) / 2
    y = (PAGE_HEIGHT - draw_h) / 2
    
    canvas.drawImage(
        ImageReader(image),
        x, y,
        width=draw_w,
        height=draw_h,
        preserveAspectRatio=True,
        mask='auto'
    )
    
    # Draw bottom text band (20% of page height)
    band_height = PAGE_HEIGHT * 0.20
    band_y = 0
    
    # Make the band slightly darker/more opaque for better text readability
    band_r = max(0, int(r * 0.85))
    band_g = max(0, int(g * 0.85))
    band_b = max(0, int(b * 0.85))
    canvas.setFillColorRGB(band_r / 255.0, band_g / 255.0, band_b / 255.0)
    canvas.setStrokeColorRGB(band_r / 255.0, band_g / 255.0, band_b / 255.0)
    canvas.rect(0, band_y, PAGE_WIDTH, band_height, stroke=0, fill=1)
    
    # Draw white text in the band
    canvas.setFillColorRGB(1, 1, 1)  # White text
    
    # Use available fonts or fallback to Helvetica
    if fonts_available:
        font_regular = 'SourceSansPro'
        font_bold = 'SourceSansPro-Bold'
        font_semibold = 'SourceSansPro-Semibold'
    else:
        font_regular = 'Helvetica'
        font_bold = 'Helvetica-Bold'
        font_semibold = 'Helvetica-Bold'
    
    # Calculate vertical positions in the band
    text_center_y = band_y + (band_height / 2)
    
    # Liturgical name (small, top of text area)
    liturgical_font_size = 18
    canvas.setFont(font_regular, liturgical_font_size)
    liturgical_width = canvas.stringWidth(liturgical_name.upper(), font_regular, liturgical_font_size)
    liturgical_x = (PAGE_WIDTH - liturgical_width) / 2
    liturgical_y = text_center_y + 35
    canvas.drawString(liturgical_x, liturgical_y, liturgical_name.upper())
    
    # Service name (large, middle)
    service_font_size = 36
    canvas.setFont(font_bold, service_font_size)
    service_width = canvas.stringWidth(service_name, font_bold, service_font_size)
    service_x = (PAGE_WIDTH - service_width) / 2
    service_y = text_center_y
    canvas.drawString(service_x, service_y, service_name)
    
    # Date (medium, bottom)
    date_font_size = 22
    canvas.setFont(font_semibold, date_font_size)
    date_width = canvas.stringWidth(service_date_str, font_semibold, date_font_size)
    date_x = (PAGE_WIDTH - date_width) / 2
    date_y = text_center_y - 40
    canvas.drawString(date_x, date_y, service_date_str)
    
    # Draw church logo in bottom right corner
    if logo_path.exists():
        try:
            logo_img = Image.open(logo_path)
            
            # Scale logo to fit ~60 points tall
            logo_height = 60
            logo_aspect = logo_img.width / logo_img.height
            logo_width = logo_height * logo_aspect
            
            # Position in bottom right corner of the band, with padding
            logo_padding = 20
            logo_x = PAGE_WIDTH - logo_width - logo_padding
            logo_y = band_y + (band_height - logo_height) / 2
            
            canvas.drawImage(
                ImageReader(logo_img),
                logo_x, logo_y,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception as exc:
            print(f"[cover_generator] Warning: Could not add logo: {exc}")
    else:
        print(f"[cover_generator] Warning: Logo not found at {logo_path}")
    
    # Finalize page
    canvas.showPage()
    canvas.save()
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# Phase 4: Pipeline Integration


def generate_auto_cover(
    service_date: date,
    service_name: str
) -> Optional[Tuple[bytes, str]]:
    """
    Automatically generate a bulletin cover for the given service.
    
    This is the main entry point that orchestrates the full workflow:
    1. Scrape UMC Discipleship for the bulletin image and liturgical name
    2. Download the image
    3. Extract a fill color from the image palette
    4. Render the branded cover PDF
    
    Args:
        service_date: The date of the Sunday service
        service_name: Name of the service (e.g., "Celebrate", "First Up")
        
    Returns:
        Tuple of (pdf_bytes, liturgical_name) if successful, None if failed
    """
    try:
        print(f"[cover_generator] Auto-generating cover for {service_name} on {service_date}")
        
        # Step 1: Scrape week info from UMC Discipleship
        week_info = scrape_week_info(service_date)
        liturgical_name = week_info.liturgical_name
        
        # Step 2: Download the bulletin image
        image = download_bulletin_image(week_info.image_url)
        
        # Step 3: Extract fill color
        fill_color = extract_fill_color(image)
        
        # Step 4: Format the service date for display
        service_date_str = service_date.strftime("%B %d, %Y")
        
        # Step 5: Generate the branded cover PDF
        pdf_bytes = generate_branded_cover_pdf(
            image=image,
            service_name=service_name,
            liturgical_name=liturgical_name,
            service_date_str=service_date_str,
            fill_color=fill_color
        )
        
        print(f"[cover_generator] Successfully generated auto cover ({len(pdf_bytes)} bytes)")
        return (pdf_bytes, liturgical_name)
        
    except Exception as exc:
        print(f"[cover_generator] Failed to auto-generate cover: {exc}")
        import traceback
        traceback.print_exc()
        return None
