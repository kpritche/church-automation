"""Automated bulletin cover generation from UMC Discipleship resources."""
from dataclasses import dataclass
from datetime import date
from typing import Optional
import re
import io

import requests
from bs4 import BeautifulSoup
from PIL import Image


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
