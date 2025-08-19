# content_parser.py
"""
Parses Planning Center items JSON from pypco and extracts text ready for slide generation.

Provides:
  - _parse_html_details(html_content) → List[str]
  - extract_items_from_pypco(item_obj, included, pco) → Dict with keys:
        item_id, title, type, html_details, text_chunks, html_present,
        is_scripture, scripture_reference, is_song

Skips items whose titles are in SKIP_TITLES (including variants of welcome and prayer items).
Supports extracting scripture reference from the item description for readings and
fetching lyrics from a lyrics.txt attachment first, then fallback to html_details for songs.
"""
import re
import html as html_mod
from typing import Any, Dict, List, Optional
import requests
import PyPDF2
from io import BytesIO

# Titles to ignore entirely (various name variants)
SKIP_TITLES = {
    "Welcome, Prelude & Lighting of Candles",
    "Pastoral Prayer",
    "Welcome,_Prelude_&_Lighting_of_Candles",
    "Pastoral_Prayer",
    "The_Pastoral_Prayer",
    "The Pastoral Prayer",
    "The Lord's Prayer",
}
# Scripture reading item titles
SCRIPTURE_TITLES = {
    "The Gospel Lesson",
    "The New Testament Lesson",
    "The Old Testament Lesson",
    "The Epistle Lesson",
    "The First Gospel Lesson",
    "The Second Gospel Lesson",
    "Scripture Reading",
    "Reading from the Psalms"
}
# Song item titles
SONG_TITLES = {"Song", "Hymn"}

# Prelude and Postlude item titles
PRELUDE_POSTLUDE_TITLES = {
    "Prelude",
    "Postlude",
    "The Postlude"
}


def _parse_html_details(html_content: str) -> List[dict]:
    """Convert ``html_details`` into clean text chunks with bold detection.

    The parser performs a lightweight HTML clean up and then splits content into
    chunks. Bold segments (``<b>`` or ``<strong>``) are extracted as their own
    chunks so they can later be rendered with yellow text. Additionally, very
    short chunks are merged with the previous chunk to avoid slides that only
    contain a couple of words.
    """

    # 1) Basic cleanup and normalisation
    content = html_mod.unescape(html_content or "")
    content = re.sub(
        r'<span[^>]*style="[^"]*(?:color\s*:\s*red|background-color)[^"]*"[^>]*>.*?</span>',
        '', content, flags=re.IGNORECASE | re.DOTALL
    )
    content = re.sub(r'<mark[^>]*>.*?</mark>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<br\s*/?>', '</p>', content, flags=re.IGNORECASE)

    chunks: List[dict] = []
    parts = re.split(r'</p>\s*', content, flags=re.IGNORECASE)

    for part in parts:
        # First split into segments that preserve bold tags
        segments = re.split(r'(<(?:b|strong)>.*?</(?:b|strong)>)', part, flags=re.IGNORECASE | re.DOTALL)
        for seg in segments:
            if not seg.strip():
                continue

            is_bold = bool(re.match(r'<(?:b|strong)>', seg, flags=re.IGNORECASE))
            seg_clean = re.sub(r'</?(?:b|strong)>', '', seg, flags=re.IGNORECASE)

            sentences = re.split(r'(?<=[\.?!])\s+', seg_clean)
            for sent in sentences:
                text = re.sub(r'<[^>]+>', '', sent).strip()
                if text:
                    chunks.append({"text": text, "is_bold": is_bold})

    # Merge very short chunks with the previous one when possible
    merged: List[dict] = []
    for chunk in chunks:
        if (
            merged
            and len(chunk["text"].split()) <= 3
            and merged[-1]["is_bold"] == chunk["is_bold"]
        ):
            merged[-1]["text"] += " " + chunk["text"]
        else:
            merged.append(chunk)

    return merged


def extract_items_from_pypco(
    item_obj: Dict[str, Any],
    included: List[Dict[str, Any]],
    pco: Any
) -> Dict[str, Any]:
    """
    Given a single item JSON and included array from pypco,
    extract html_details, text_chunks, detect scripture/song, and return metadata.
    """
    parsed_chunks: List[Dict] = []
    attrs = item_obj.get('attributes', {}) or {}
    item_id = str(item_obj.get('id'))
    item_type = (attrs.get('item_type') or '').strip() or 'Item'
    title = attrs.get('title') or attrs.get('display_name') or item_type

    # Capture raw html_details and description
    html_detail = attrs.get('html_details') or ''
    description = attrs.get('description') or ''
    

    # Skip unwanted items
    if title.strip() in SKIP_TITLES:
        return {
            'item_id': item_id,
            'title': title,
            'type': item_type,
            'html_details': html_detail,
            'parsed_chunks': [],
            'text_chunks': [],
            'html_present': False,
            'is_scripture': False,
            'scripture_reference': None,
            'is_song': False
        }

    # Identify type flags
    stripped_title = title.strip()
    is_scripture = stripped_title in SCRIPTURE_TITLES
    is_song = stripped_title in SONG_TITLES
    is_prelude_postlude = stripped_title in PRELUDE_POSTLUDE_TITLES
    scripture_reference: Optional[str] = None
    text_chunks: List[str] = []

    # Scripture: use description for reference, then parse html_details
    if is_scripture:
        if description.strip():
            scripture_reference = description.strip()
        if html_detail.strip():
            parsed_chunks = _parse_html_details(html_detail)
            text_chunks = [c["text"] for c in parsed_chunks]

    elif is_prelude_postlude and html_detail.strip():
        # Prelude/Postlude: ignore line breaks and keep all text on one slide
        content = html_mod.unescape(html_detail)
        content = re.sub(r'<br\s*/?>', ' ', content, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'\s+', ' ', text).strip()
        is_bold = bool(re.search(r'<(?:b|strong)[^>]*>', html_detail, flags=re.IGNORECASE))
        parsed_chunks = [{"text": text, "is_bold": is_bold}]
        text_chunks = [text]

    # # Song: look in attachments first, then html_details fallback
    # elif is_song or item_type.lower() == "song":
    #     return {
    #         'item_id': item_id,
    #         'title': title,
    #         'type': item_type,
    #         'html_details': html_detail,
    #         'text_chunks': [],
    #         'html_present': False,
    #         'is_scripture': False,
    #         'scripture_reference': None,
    #         'is_song': False
    #     }
        # # 1) Try the lyrics.txt (or *Lyrics*) attachment
        # attach_url = item_obj['links']['self'] + '/attachments'
        # resp = pco.get(attach_url)
        # text_chunks = []
        # for att in resp.get('data', []):
        #     fn = att['attributes'].get('filename', '').lower()
        #     if fn.endswith(('lyrics.pdf', '.txt')):
        #         dl = att['id']
        #         print(dl)
        #         if not dl:
        #             continue

        #         data = pco.get('/services/v2/attachments/' + dl + '/open')
        #         print(data)
        #         if fn.endswith('.pdf'):
        #             # Extract from PDF
        #             reader = PyPDF2.PdfReader(BytesIO(data))
        #             raw = "\n\n".join(
        #                 page.extract_text() or "" for page in reader.pages
        #             )
        #         else:
        #             # Extract from plain text
        #             raw = data.decode('utf-8', errors='ignore')

        #         # Split into paragraphs
        #         text_chunks = [
        #             para.strip()
        #             for para in raw.split('\n\n')
        #             if para.strip()
        #         ]
        #         break

        # # 2) Fallback to HTML details if no attachment found
        # if not text_chunks and html_detail.strip():
        #     text_chunks = _parse_html_details(html_detail)

        # # 3) Remove any verse/chorus/bridge lines or leading numbers
        # cleaned: List[str] = []
        # for line in text_chunks:
        #     if re.match(r'^\s*(\d+|verse|chorus|refrain|bridge|tag|ending)\b', line, flags=re.IGNORECASE):
        #         continue
        #     cleaned.append(line)
        # text_chunks = cleaned

    # Other items: use HTML by default
    else:
        if html_detail.strip():
            parsed_chunks = _parse_html_details(html_detail)
            text_chunks = [c["text"] for c in parsed_chunks]

    html_present = bool(text_chunks)

    return {
        'item_id': item_id,
        'title': title,
        'type': item_type,
        'html_details': html_detail,
        'parsed_chunks':parsed_chunks,
        'text_chunks': text_chunks,
        'html_present': html_present,
        'is_scripture': is_scripture,
        'scripture_reference': scripture_reference,
        'is_song': is_song
    }
