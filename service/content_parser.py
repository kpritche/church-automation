# content_parser.py
"""
Parses Planning Center items JSON from pypco and extracts text ready for slide generation.

Provides:
  - _parse_html_details(html_content) → List[str]
  - extract_items_from_pypco(item_obj, included, pco) → Dict with keys:
        item_id, title, type, text_chunks, html_present

Usage (in make_service_slides.py):
    parsed = extract_items_from_pypco(item_obj, included, pco)
"""
import re
import html as html_mod
from typing import Any, Dict, List


def _parse_html_details(html_content: str) -> List[str]:
    """
    Convert html_details into clean text chunks:
      - Unescape HTML
      - Remove red/highlighted spans and <mark> tags
      - Normalize <br> to paragraph break
      - Split on </p> and sentence-ending punctuation
      - Strip remaining tags
    """
    content = html_mod.unescape(html_content or "")
    # remove red or highlighted spans
    content = re.sub(
        r'<span[^>]*style="[^"]*(?:color\s*:\s*red|background-color)[^"]*"[^>]*>.*?</span>',
        '', content, flags=re.IGNORECASE | re.DOTALL
    )
    content = re.sub(r'<mark[^>]*>.*?</mark>', '', content, flags=re.IGNORECASE | re.DOTALL)
    # normalize <br> to paragraph boundary
    content = re.sub(r'<br\s*/?>', '</p>', content, flags=re.IGNORECASE)

    chunks: List[str] = []
    # split on paragraph close
    parts = re.split(r'</p>\s*', content, flags=re.IGNORECASE)
    for part in parts:
        # split on sentence-ending punctuation
        sentences = re.split(r'(?<=[\.?!])\s+', part)
        for sent in sentences:
            text = re.sub(r'<[^>]+>', '', sent).strip()
            if text:
                chunks.append(text)
    return chunks


def extract_items_from_pypco(
    item_obj: Dict[str, Any],
    included: List[Dict[str, Any]],
    pco: Any
) -> Dict[str, Any]:
    """
    Given a single item JSON and included array from pypco,
    extract the HTML detail text into chunks and indicate presence.

    Returns a dict:
      {
        'item_id': str,
        'title': str,
        'type': str,
        'text_chunks': List[str],
        'html_present': bool
      }
    """
    attrs = item_obj.get('attributes', {}) or {}
    item_id = str(item_obj.get('id'))
    item_type = (attrs.get('item_type') or '').strip() or 'Item'
    title = attrs.get('title') or attrs.get('display_name') or item_type

    # Skip html for a specific item
    html_detail = attrs.get('html_details') if title != 'Welcome, Prelude, & Lighting of Candles' else ''
    html_present = bool(html_detail and html_detail.strip())

    text_chunks: List[str] = []
    if html_present:
        text_chunks = _parse_html_details(html_detail)

    return {
        'item_id': item_id,
        'title': title,
        'type': item_type,
        'text_chunks': text_chunks,
        'html_present': html_present
    }
