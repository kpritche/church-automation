"""Automated bulletin cover generation from UMC Discipleship resources."""
from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple
import re
import io
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFilter, ImageFont
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
    
    week_url: Optional[str] = None
    liturgical_name: Optional[str] = None
    
    # Method 1: Look for <span class="date-text"> elements with the target date
    # Preferred method for structured HTML
    date_spans = soup.find_all('span', class_='date-text')
    for span in date_spans:
        span_text = span.get_text(strip=True)
        parsed_date = _parse_date_from_string(span_text)
        
        if parsed_date == service_date:
            # Found the date span
            # Look for sibling <span class="page-secondary-text"> for liturgical name
            parent = span.parent
            if parent:
                secondary_span = parent.find('span', class_='page-secondary-text')
                if secondary_span:
                    liturgical_name = secondary_span.get_text(strip=True)
                
                # Find the link in the next <p> tag or nearby structure
                # The structure is: <p><date spans></p><p><series link><week link></p>
                next_p = parent.find_next_sibling('p')
                if next_p:
                    # Look for <span class="week-title"><a> for the week URL
                    week_title_span = next_p.find('span', class_='week-title')
                    if week_title_span:
                        link = week_title_span.find('a', href=True)
                        if link:
                            week_url = link['href']
            
            if week_url and liturgical_name:
                break
    
    # Method 2: Fallback to text parsing if structured HTML didn't work
    if not week_url or not liturgical_name:
        text_content = soup.get_text()
        lines = text_content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            parsed_date = _parse_date_from_string(line)
            
            if parsed_date == service_date:
                # Extract liturgical name from this line (everything after the date)
                date_match = re.search(r'([A-Z]+\s+\d+,\s+\d{4})\s*(.*)', line.upper())
                if date_match:
                    temp_liturgical = date_match.group(2).strip()
                    if temp_liturgical and not liturgical_name:
                        liturgical_name = temp_liturgical
                
                # Find links that contain this liturgical name
                if liturgical_name:
                    for link in soup.find_all('a', href=True):
                        link_text = link.get_text().strip().upper()
                        if liturgical_name in link_text and 'lectionary' not in link['href']:
                            # Found a link containing the liturgical name
                            # Make sure it's a planning page, not the series page
                            if 'week' in link['href'].lower() or liturgical_name.replace(',', '').replace(' ', '-').lower() in link['href'].lower():
                                week_url = link['href']
                                break
                
                if week_url and liturgical_name:
                    break
    
    if not week_url or not liturgical_name:
        raise ValueError(
            f"No lectionary entry found for {service_date.strftime('%B %d, %Y')}. "
            f"Found week_url={week_url}, liturgical_name={liturgical_name}"
        )
    
    # Derive the graphics page URL
    # Pattern: {week_url}/{week_name}-graphics
    # Example: .../week-2-third-sunday-of-easter-year-a/week-2-third-sunday-of-easter-year-a-graphics
    graphics_url = week_url.rstrip('/')
    week_name = graphics_url.split('/')[-1]  # Get the last part of the URL
    
    # Strip -lectionary-planning-notes suffix if present
    if week_name.endswith('-lectionary-planning-notes'):
        week_name = week_name[:-len('-lectionary-planning-notes')]
    
    graphics_url = f"{graphics_url}/{week_name}-graphics"
    
    print(f"[cover_generator] Fetching graphics page: {graphics_url}")
    graphics_response = requests.get(graphics_url, timeout=REQUEST_TIMEOUT)
    graphics_response.raise_for_status()
    
    graphics_soup = BeautifulSoup(graphics_response.text, 'html.parser')
    
    # Find the social media image download link (larger, better quality than bulletin)
    # Look for text containing "SOCIAL" followed by a download link
    social_url: Optional[str] = None
    
    for element in graphics_soup.find_all(string=re.compile(r'SOCIAL', re.IGNORECASE)):
        # Find the next <a> tag with "Download" text
        parent = element.parent
        if parent:
            # Look for a link in the parent or nearby siblings
            for link in parent.find_all('a', href=True):
                if 'download' in link.get_text().lower() or link['href'].endswith(('.jpg', '.jpeg', '.png')):
                    social_url = link['href']
                    break
            
            # Also check next siblings
            if not social_url:
                next_sibling = parent.find_next_sibling()
                while next_sibling and not social_url:
                    for link in next_sibling.find_all('a', href=True):
                        if 'download' in link.get_text().lower() or link['href'].endswith(('.jpg', '.jpeg', '.png')):
                            social_url = link['href']
                            break
                    next_sibling = next_sibling.find_next_sibling()
        
        if social_url:
            break
    
    # Fallback: if Social not found, try replacing _Bulletin with _Social in any found image URL
    if not social_url:
        for link in graphics_soup.find_all('a', href=True):
            if '_Bulletin.jpg' in link['href']:
                social_url = link['href'].replace('_Bulletin.jpg', '_Social.jpg')
                print(f"[cover_generator] Using Social image variant: {social_url}")
                break
    
    if not social_url:
        raise ValueError(f"Could not find social media image download link on {graphics_url}")
    
    print(f"[cover_generator] Found social media image: {social_url}")
    
    return CoverWeekInfo(
        liturgical_name=liturgical_name,
        image_url=social_url
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
    Extract a suitable background fill color from the image using dominant color analysis.
    
    Uses histogram-based color analysis to find truly dominant colors in the image,
    then selects the best one based on:
    - Good contrast with white text (WCAG AA: ≥4.5:1)
    - Lighter, softer colors preferred (medium-to-light luminance)
    - Color saturation and appearance in the image
    
    Falls back to a soft peachy tan if no suitable color found.
    
    Args:
        image: PIL Image to analyze
        
    Returns:
        RGB color tuple (0-255 for each channel)
    """
    FALLBACK_SOFT_COLOR = (220, 200, 180)  # Very light peachy tan
    MIN_CONTRAST = 4.5  # WCAG AA standard
    MIN_LUMINANCE = 0.30  # Exclude dark colors
    PREFERRED_LUMINANCE_MIN = 0.50  # Prefer lighter, softer colors
    PREFERRED_LUMINANCE_MAX = 0.80  # Extended to include very light colors
    
    try:
        # Resize image for faster processing
        img_small = image.copy()
        img_small.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed
        if img_small.mode != 'RGB':
            img_small = img_small.convert('RGB')
        
        # Get pixel data and count color frequencies
        pixels = list(img_small.getdata())
        
        # Build color frequency map, grouping similar colors
        color_freq = {}
        for pixel in pixels:
            # Round to nearest 16 to group similar colors
            rounded = tuple((c // 16) * 16 for c in pixel)
            color_freq[rounded] = color_freq.get(rounded, 0) + 1
        
        # Sort by frequency to get most dominant colors
        sorted_colors = sorted(color_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Extract top colors
        colors = [color for color, freq in sorted_colors[:20]]
        
        # Find soft colors with good contrast
        best_color = None
        best_score = -1.0
        
        for color in colors:
            contrast = wcag_contrast_ratio(color)
            
            # Skip if doesn't meet minimum contrast
            if contrast < MIN_CONTRAST:
                continue
            
            # Calculate perceived luminance
            luminance = (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]) / 255.0
            
            # Exclude very dark/black colors
            if luminance < MIN_LUMINANCE:
                continue
            
            # Calculate color saturation (preference for more saturated/colorful over gray)
            max_channel = max(color)
            min_channel = min(color)
            saturation = (max_channel - min_channel) / max(max_channel, 1) if max_channel > 0 else 0
            
            # Scoring: prefer colors in the soft/medium-light luminance range
            if PREFERRED_LUMINANCE_MIN <= luminance <= PREFERRED_LUMINANCE_MAX:
                # In preferred range - score based on how close to upper end (prefer lighter)
                luminance_score = 0.7 + 0.3 * ((luminance - PREFERRED_LUMINANCE_MIN) / (PREFERRED_LUMINANCE_MAX - PREFERRED_LUMINANCE_MIN))
            else:
                # Outside preferred range - significantly lower score
                if luminance < PREFERRED_LUMINANCE_MIN:
                    # Below range - heavily penalize darker colors
                    luminance_score = 0.3 * (luminance / PREFERRED_LUMINANCE_MIN)
                else:
                    # Above range - slightly penalize very light colors
                    luminance_score = 0.6 * ((1.0 - luminance) / (1.0 - PREFERRED_LUMINANCE_MAX))
            
            # Bonus for adequate contrast (but don't require extreme contrast)
            contrast_score = min(1.0, (contrast - MIN_CONTRAST) / 10.0)
            
            # Bonus for saturation (prefer actual colors over grays)
            saturation_score = saturation * 0.5  # 0 to 0.5 bonus
            
            # Combined score: luminance (75%), saturation (15%), contrast (10%)
            score = luminance_score * 0.75 + saturation_score * 0.15 + contrast_score * 0.10
            
            if score > best_score:
                best_score = score
                best_color = color
        
        if best_color:
            print(f"[cover_generator] Selected fill color: RGB{best_color} (contrast: {wcag_contrast_ratio(best_color):.1f}:1)")
            return best_color
        else:
            print(f"[cover_generator] No suitable palette color found, using soft fallback color")
            return FALLBACK_SOFT_COLOR
    
    except Exception as exc:
        print(f"[cover_generator] Error extracting fill color: {exc}, using soft fallback color")
        return FALLBACK_SOFT_COLOR


# Phase 3: Cover Page Renderer


def _render_text_with_shadow(
    text: str,
    font_path: Path,
    font_size: int,
    shadow_offset: Tuple[int, int] = (4, 4),
    shadow_blur: int = 5,
    shadow_color: Tuple[int, int, int, int] = (70, 58, 50, 110),
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    scale: int = 2,
) -> Image.Image:
    """Render text with a light drop shadow to an RGBA image."""
    sized_font = ImageFont.truetype(str(font_path), font_size * scale)
    scratch = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    scratch_draw = ImageDraw.Draw(scratch)
    bbox = scratch_draw.textbbox((0, 0), text, font=sized_font)

    blur_margin = max(8, shadow_blur + max(abs(shadow_offset[0]), abs(shadow_offset[1])) + 6)
    padding = blur_margin * scale
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    image_width = text_width + (padding * 2) + abs(shadow_offset[0] * scale)
    image_height = text_height + (padding * 2) + abs(shadow_offset[1] * scale)
    origin_x = padding - bbox[0]
    origin_y = padding - bbox[1]

    shadow_layer = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    shadow_draw.text(
        (origin_x + shadow_offset[0] * scale, origin_y + shadow_offset[1] * scale),
        text,
        font=sized_font,
        fill=shadow_color,
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur * scale / 2))

    text_layer = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((origin_x, origin_y), text, font=sized_font, fill=text_color)

    composite = Image.alpha_composite(shadow_layer, text_layer)
    composite_bbox = composite.getbbox()
    if composite_bbox:
        composite = composite.crop(composite_bbox)
    return composite


def _render_logo_shadow(logo_image: Image.Image, blur_radius: int = 6) -> Image.Image:
    """Create a soft shadow image from the logo alpha channel."""
    logo_rgba = logo_image.convert("RGBA")
    alpha = logo_rgba.getchannel("A")
    shadow_alpha = alpha.point(lambda value: min(255, int(value * 0.38)))
    shadow = Image.new("RGBA", logo_rgba.size, (70, 58, 50, 0))
    shadow.putalpha(shadow_alpha)
    return shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))


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
    
    font_regular_path = FONTS_DIR / "SourceSansPro-Regular.ttf"
    font_black_path = FONTS_DIR / "SourceSansPro-Black.ttf"
    service_font_candidates = [
        FONTS_DIR / "CoconPro-Bold.otf",
        FONTS_DIR / "CoconRegularFont.otf",
        FONTS_DIR / "CoconPro-Regular.otf",
    ]
    service_font_path = next(
        (candidate for candidate in service_font_candidates if candidate.exists()),
        service_font_candidates[0],
    )

    # Register Source Sans fallbacks for any direct canvas text usage.
    fonts_available = {
        'SourceSansPro': False,
        'SourceSansPro-Bold': False,
        'SourceSansPro-Semibold': False,
        'SourceSansPro-Black': False,
    }
    
    try:
        font_bold = FONTS_DIR / "SourceSansPro-Bold.ttf"
        font_semibold = FONTS_DIR / "SourceSansPro-Semibold.ttf"
        
        if 'SourceSansPro' not in pdfmetrics.getRegisteredFontNames():
            if font_regular_path.exists():
                try:
                    pdfmetrics.registerFont(TTFont('SourceSansPro', str(font_regular_path)))
                    fonts_available['SourceSansPro'] = True
                except Exception as e:
                    print(f"[cover_generator] Could not register SourceSansPro: {e}")
        else:
            fonts_available['SourceSansPro'] = True
            
        if 'SourceSansPro-Bold' not in pdfmetrics.getRegisteredFontNames():
            if font_bold.exists():
                try:
                    pdfmetrics.registerFont(TTFont('SourceSansPro-Bold', str(font_bold)))
                    fonts_available['SourceSansPro-Bold'] = True
                except Exception as e:
                    print(f"[cover_generator] Could not register SourceSansPro-Bold: {e}")
        else:
            fonts_available['SourceSansPro-Bold'] = True
            
        if 'SourceSansPro-Semibold' not in pdfmetrics.getRegisteredFontNames():
            if font_semibold.exists():
                try:
                    pdfmetrics.registerFont(TTFont('SourceSansPro-Semibold', str(font_semibold)))
                    fonts_available['SourceSansPro-Semibold'] = True
                except Exception as e:
                    print(f"[cover_generator] Could not register SourceSansPro-Semibold: {e}")
        else:
            fonts_available['SourceSansPro-Semibold'] = True
            
        if 'SourceSansPro-Black' not in pdfmetrics.getRegisteredFontNames():
            if font_black_path.exists():
                try:
                    pdfmetrics.registerFont(TTFont('SourceSansPro-Black', str(font_black_path)))
                    fonts_available['SourceSansPro-Black'] = True
                except Exception as e:
                    print(f"[cover_generator] Could not register SourceSansPro-Black: {e}")
        else:
            fonts_available['SourceSansPro-Black'] = True
            
    except Exception as exc:
        print(f"[cover_generator] Warning: Error during font registration: {exc}")
    
    # Create PDF canvas
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    
    # Fill background with fill_color
    r, g, b = fill_color
    canvas.setFillColorRGB(r / 255.0, g / 255.0, b / 255.0)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    
    # Draw image BOTTOM-ALIGNED (scaled to fit width)
    img_w, img_h = image.size
    # Scale to fit page width
    scale = PAGE_WIDTH / img_w
    draw_w = PAGE_WIDTH
    draw_h = img_h * scale
    
    # Position at bottom of page (y=0), centered horizontally
    x = 0
    y = 0  # Bottom-aligned
    
    # If image is taller than page, scale to fit height instead
    if draw_h > PAGE_HEIGHT:
        scale = PAGE_HEIGHT / img_h
        draw_w = img_w * scale
        draw_h = PAGE_HEIGHT
        x = (PAGE_WIDTH - draw_w) / 2
    
    canvas.drawImage(
        ImageReader(image),
        x, y,
        width=draw_w,
        height=draw_h,
        preserveAspectRatio=True,
        mask='auto'
    )
    
    # Text positioning
    text_left_margin = 40
    text_top_margin = 24
    
    # Clean up service name: remove " Service" suffix (case-insensitive)
    display_service_name = service_name
    if service_name.lower().endswith(' service'):
        display_service_name = service_name[:-8]  # Remove " Service"
    
    # Clean up liturgical name: remove ", Year X" suffix
    display_liturgical_name = liturgical_name
    import re
    display_liturgical_name = re.sub(r',\s*Year\s+[ABC]\s*$', '', liturgical_name, flags=re.IGNORECASE)

    service_font_file = service_font_path if service_font_path.exists() else font_black_path
    text_font_file = font_black_path if font_black_path.exists() else font_regular_path

    service_font_size = 60
    service_text_image = _render_text_with_shadow(
        display_service_name,
        service_font_file,
        service_font_size,
        shadow_offset=(5, 5),
        shadow_blur=5,
    )

    liturgical_font_size = 32
    liturgical_text_image = _render_text_with_shadow(
        display_liturgical_name,
        text_font_file,
        liturgical_font_size,
        shadow_offset=(4, 4),
        shadow_blur=4,
    )

    date_font_size = 26
    date_text_image = _render_text_with_shadow(
        service_date_str,
        text_font_file,
        date_font_size,
        shadow_offset=(4, 4),
        shadow_blur=4,
    )

    service_draw_w = service_text_image.width / 2
    service_draw_h = service_text_image.height / 2
    liturgical_draw_w = liturgical_text_image.width / 2
    liturgical_draw_h = liturgical_text_image.height / 2
    date_draw_w = date_text_image.width / 2
    date_draw_h = date_text_image.height / 2

    top_text_area = PAGE_HEIGHT - draw_h
    gap_after_service = 8
    gap_after_liturgical = 8
    stack_height = service_draw_h + gap_after_service + liturgical_draw_h + gap_after_liturgical + date_draw_h
    available_stack_height = max(80, top_text_area - text_top_margin - 10)
    if stack_height > available_stack_height:
        gap_after_service = 4
        gap_after_liturgical = 4
        stack_height = service_draw_h + gap_after_service + liturgical_draw_h + gap_after_liturgical + date_draw_h

    current_top = PAGE_HEIGHT - text_top_margin
    canvas.drawImage(
        ImageReader(service_text_image),
        text_left_margin,
        current_top - service_draw_h,
        width=service_draw_w,
        height=service_draw_h,
        mask='auto'
    )
    current_top -= service_draw_h + gap_after_service
    canvas.drawImage(
        ImageReader(liturgical_text_image),
        text_left_margin,
        current_top - liturgical_draw_h,
        width=liturgical_draw_w,
        height=liturgical_draw_h,
        mask='auto'
    )
    current_top -= liturgical_draw_h + gap_after_liturgical
    canvas.drawImage(
        ImageReader(date_text_image),
        text_left_margin,
        current_top - date_draw_h,
        width=date_draw_w,
        height=date_draw_h,
        mask='auto'
    )
    
    # Draw church logo LARGE in bottom right corner (approximately half page width)
    if logo_path.exists():
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            
            # Scale logo to approximately half page width (~300 points)
            logo_width = PAGE_WIDTH * 0.5  # Half page width
            logo_aspect = logo_img.width / logo_img.height
            logo_height = logo_width / logo_aspect
            
            # Position in bottom right corner, aligned to edges
            logo_padding = 0  # No padding - align with edges
            logo_x = PAGE_WIDTH - logo_width - logo_padding
            logo_y = logo_padding

            logo_shadow = _render_logo_shadow(logo_img)
            canvas.drawImage(
                ImageReader(logo_shadow),
                logo_x + 4,
                logo_y + 4,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            
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
