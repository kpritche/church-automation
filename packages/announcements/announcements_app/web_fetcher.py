"""Fetch announcements from FUMC website."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional
import requests
from bs4 import BeautifulSoup


def fetch_latest_announcement_html(website_url: str = "https://www.fumcwl.org/weekly-events/") -> str:
    """Fetch the most recent announcement HTML from the FUMC website.
    
    Args:
        website_url: URL of the weekly events page
        
    Returns:
        HTML content of the most recent announcement
        
    Raises:
        RuntimeError: If unable to fetch or parse the page
    """
    print(f"   Fetching weekly events page: {website_url}")
    
    try:
        # Fetch the weekly events page
        response = requests.get(website_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch weekly events page: {e}")
    
    # Parse the page to find announcement links
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links matching the pattern "View Weekly Events – <month> <day1> - <day2>, <year>"
    # Pattern: "View Weekly Events – January 23 - 29, 2026"
    link_pattern = re.compile(r'View Weekly Events\s*–\s*(\w+)\s+(\d+)\s*-\s*(\d+),\s*(\d{4})')
    
    announcement_links = []
    for link in soup.find_all('a', href=True):
        link_text = link.get_text(strip=True)
        match = link_pattern.match(link_text)
        if match:
            month_name, day1, day2, year = match.groups()
            try:
                # Parse the first date to use for sorting (Thursday of the week)
                date_obj = datetime.strptime(f"{month_name} {day1}, {year}", "%B %d, %Y")
                announcement_links.append({
                    'url': link['href'],
                    'text': link_text,
                    'date': date_obj
                })
            except ValueError:
                # Skip if date parsing fails
                continue
    
    if not announcement_links:
        raise RuntimeError("No announcement links found on the weekly events page")
    
    # Sort by date (most recent first)
    announcement_links.sort(key=lambda x: x['date'], reverse=True)
    most_recent = announcement_links[0]
    
    print(f"   Found {len(announcement_links)} announcement(s)")
    print(f"   Most recent: {most_recent['text']}")
    print(f"   URL: {most_recent['url']}")
    
    # Fetch the announcement page
    try:
        ann_response = requests.get(most_recent['url'], timeout=10)
        ann_response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch announcement page: {e}")
    
    print(f"   ✓ Fetched announcement HTML ({len(ann_response.text)} chars)")
    
    return ann_response.text
