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
# Optional imports only needed for attachment/PDF features. Make them lazy-safe
# so ad-hoc tests can run without installing extras.
try:  # pragma: no cover - optional dependency
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore
try:  # pragma: no cover - optional dependency
    import PyPDF2  # type: ignore
    from io import BytesIO  # type: ignore
except Exception:  # pragma: no cover
    PyPDF2 = None  # type: ignore
    BytesIO = None  # type: ignore
try:  # pragma: no cover - optional dependency
    from PyPDF2 import PdfReader  # type: ignore
    import io  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore
    io = None  # type: ignore

# Titles to ignore entirely (various name variants)
SKIP_TITLES = {
    "Welcome, Prelude & Lighting of Candles",
    "Pastoral Prayer",
    "Welcome,_Prelude_&_Lighting_of_Candles",
    "Pastoral_Prayer",
    "The_Pastoral_Prayer",
    "The Pastoral Prayer",
    "The Lord's Prayer",
    "The Call to Fly"
}
# Scripture reading item titles
SCRIPTURE_TITLES = {
    "The Gospel Lesson",
    "The Gospel Lesson I",
    "The Gospel Lesson II",
    "The Gospel Lesson III",
    "The New Testament Lesson",
    "The Old Testament Lesson",
    "The Epistle Lesson",
    "The First Gospel Lesson",
    "The Second Gospel Lesson",
    "Scripture Reading",
    "Reading from the Psalms",
    "A Story about Compassion",
    "Lesson from the Old Testament",
    "Lesson from the New Testament",
    "Scripture"
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
    """Convert ``html_details`` into clean, phrase-sized chunks with bold detection.

    Goals:
      - Respect lyric phrasing: favor splits at commas/semicolons/dashes within
        sentences, not only full stops.
      - Avoid tiny chunks: merge short phrases so slides don’t end up with single
        words or very short fragments.
      - Preserve bold segments as separate chunks so they can be styled later.
    """
    # Tunable heuristics for natural phrases
    MIN_WORDS = 4
    MAX_WORDS = 18

    def count_words(s: str) -> int:
        return len([w for w in s.strip().split() if w])

    def split_into_phrases(text: str) -> List[str]:
        """Split a sentence-like string into musical/lyrical phrases.

        Strategy:
          1) Split hard at end-of-sentence punctuation (.?!).
          2) Within each sentence, split on commas/semicolons/colons/em-dash to
             form sub-phrases that are at least MIN_WORDS and at most MAX_WORDS
             when possible.
          3) Merge any leftover sub-phrases that are too short with neighbors.
        """
        # Normalize em-dash and various separators to assist splitting
        t = text.replace("\u2014", " — ")  # em dash
        # First split by sentence enders; keep punctuation with the segment
        sentences = re.split(r"(?<=[\.!?])\s+", t)

        phrases: List[str] = []
        for sent in sentences:
            s = sent.strip()
            if not s:
                continue
            # Identify if the sentence ended with a strong terminator
            end_punct_match = re.search(r"[\.!?]+$", s)
            end_punct = end_punct_match.group(0) if end_punct_match else ""
            core = s[:-len(end_punct)] if end_punct else s

            # Secondary splits at commas/semicolon/colon/em-dash — but preserve
            # the delimiter so punctuation (especially ':') is not lost.
            tokens = re.split(r"\s*([,;:\u2014—])\s*", core)
            # Build clause fragments with their trailing delimiter attached
            clause_frags: List[str] = []
            i = 0
            while i < len(tokens):
                part = (tokens[i] or '').strip()
                delim = ''
                if i + 1 < len(tokens) and tokens[i + 1] in {',', ';', ':', '\u2014', '—'}:
                    delim = tokens[i + 1]
                    i += 2
                else:
                    i += 1
                if part:
                    clause_frags.append(part + delim)

            current: List[str] = []
            current_words = 0
            subphrases: List[str] = []

            for frag in clause_frags:
                w = count_words(frag)
                if current_words == 0:
                    current = [frag]
                    current_words = w
                    continue

                if current_words + w <= MAX_WORDS:
                    current.append(frag)
                    current_words += w
                else:
                    # If the new fragment is short, prefer to keep it together
                    if w < MIN_WORDS and current_words <= MAX_WORDS:
                        current.append(frag)
                        current_words += w
                    else:
                        subphrases.append(" ".join(x for x in current if x))
                        current = [frag]
                        current_words = w

            if current_words:
                subphrases.append(" ".join(x for x in current if x))

            # Merge too-short subphrases with neighbors
            merged: List[str] = []
            for sp in subphrases:
                if merged and count_words(sp) < MIN_WORDS:
                    merged[-1] = f"{merged[-1]} {sp}".strip()
                else:
                    merged.append(sp)

            # Attach the terminal punctuation to the last phrase
            if merged:
                merged[-1] = (merged[-1] + end_punct).strip()

            phrases.extend(merged)

        # Final safety merge: avoid leading tiny phrase
        safe: List[str] = []
        for ph in phrases:
            if safe and count_words(ph) < MIN_WORDS:
                safe[-1] = f"{safe[-1]} {ph}".strip()
            else:
                safe.append(ph)
        return [p for p in safe if p]

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

            # Remove residual tags and split into natural phrases
            seg_text = re.sub(r'<[^>]+>', '', seg_clean)
            for phrase in split_into_phrases(seg_text):
                text = phrase.strip()
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
            merged[-1]["text"] = (merged[-1]["text"] + ", " + chunk["text"]).strip(', ')
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
    # Check both title (for "Song"/"Hymn") and item_type from Planning Center
    is_song = stripped_title in SONG_TITLES or item_type.lower() == "song"
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


def has_pro_attachment(
    pco,
    service_type_id: int,
    plan_id: str,
    item_id: str,
) -> bool:
    """Check if an item already has a .pro file attached.
    
    Returns True if a .pro file is already attached to the item, False otherwise.
    """
    try:
        attachments_url = (
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
        )
        resp = pco.get(attachments_url)
        attachments = resp.get("data") or []
        
        # Check if any attachment is a .pro file
        for att in attachments:
            att_attrs = att.get("attributes") or {}
            filename = (att_attrs.get("filename") or "").lower()
            if filename.endswith(".pro"):
                return True
    except Exception as exc:
        print(f"[warn] Unable to check attachments for item {item_id}: {exc}")
    
    return False


def fetch_lyrics_attachments(
    pco,
    lyrics_items: List[Dict[str, object]],
    service_type_id: int,
    plan_id: str,
    included: Optional[List[Dict[str, object]]] = None,
) -> List[Dict[str, object]]:
    """Fetch lyrics PDF attachments for song items.
    
    Returns list of dicts with 'title' and 'attachment_obj' for lyrics PDFs.
    """
    lyrics_attachments: List[Dict[str, object]] = []
    
    for song_info in lyrics_items:
        item_obj = song_info["item_obj"]
        title = song_info["title"]
        item_id = str(item_obj.get("id", ""))
        
        # Try to get all attachments for this item
        attachments_url = (
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
        )
        try:
            resp = pco.get(attachments_url)
            attachments = resp.get("data") or []
            
            # Find the lyrics PDF (filename ends with 'lyrics.pdf')
            for att in attachments:
                att_attrs = att.get("attributes") or {}
                filename = (att_attrs.get("filename") or "").lower()
                if filename.endswith("lyrics.pdf"):
                    att_id = str(att.get("id"))
                    lyrics_attachments.append({
                        "title": title,
                        "attachment_obj": att,
                        "item_id": item_id,
                    })
                    break
        except Exception as exc:
            print(f"[warn] Unable to fetch attachments for song '{title}': {exc}")
    
    return lyrics_attachments


def download_lyrics_pdf(
    attachment_obj: Dict[str, object],
    pco,
    service_type_id: int,
    plan_id: str,
    item_id: str
) -> Optional[bytes]:
    """Download a lyrics PDF using the attachment object.
    
    Uses the Planning Center API's attachment open endpoint to get a direct download URL.
    
    Returns PDF bytes or None if download fails.
    """
    if requests is None:
        print("[WARN] requests module not available; cannot download lyrics PDF")
        return None
    
    att_id = str(attachment_obj.get("id", ""))
    att_attrs = attachment_obj.get("attributes") or {}
    filename = att_attrs.get("filename", "")
    
    # Use the full path to open the attachment via PCO API
    open_endpoint = (
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/"
        f"items/{item_id}/attachments/{att_id}/open"
    )
    
    try:
        # Make a POST request to the open endpoint (following the same pattern as cover attachments)
        resp = pco.post(open_endpoint)
        
        # Extract the actual download URL from the response
        attachment_url: Optional[str] = None
        if isinstance(resp, dict):
            attachment_url = (
                resp.get("data", {}).get("attributes", {}).get("attachment_url")
                or resp.get("attachment_url")
            )
        
        if not attachment_url:
            print(f"[WARN] Could not resolve attachment_url for {att_id}; response: {resp}")
            return None
        
        # Download the file from the resolved URL (no auth needed, it's a signed URL)
        file_resp = requests.get(attachment_url)
        file_resp.raise_for_status()
        content = file_resp.content
        
        # Verify it's a PDF
        if content[:4].upper() == b"%PDF":
            return content
        else:
            print(f"[WARN] Downloaded content is not a PDF for attachment {att_id}")
            return None
            
    except Exception as exc:
        print(f"[WARN] Failed to download lyrics PDF for attachment {att_id}: {exc}")
        return None


def extract_lyrics_text(pdf_bytes: bytes, song_title: str) -> Optional[str]:
    """Extract and clean text from a lyrics PDF.
    
    Removes common headers, footers, formatting artifacts, and text in square brackets.
    
    Returns cleaned lyrics text or None if extraction fails.
    """
    if PdfReader is None or io is None:
        print("[WARN] PyPDF2 module not available; cannot extract lyrics from PDF")
        return None
    
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        all_text = ""
        
        # Extract text from all pages
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                all_text += text + "\n"
        
        if not all_text.strip():
            print(f"[WARN] No text extracted from lyrics PDF for '{song_title}'")
            return None
        
        # Remove text in square brackets [like this]
        all_text = re.sub(r'\[.*?\]', '', all_text)
        
        # Clean up the text
        lines = all_text.split("\n")
        cleaned_lines: List[str] = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip arrangement information (like "Intro, V1, C, Inter, V2, C, Inst, C, Rf, C, Tag, Outro, E")
            # These lines typically have multiple commas and common arrangement abbreviations
            if ',' in line:
                lower_line = line.lower()
                arrangement_markers = ['intro', 'outro', 'inst', 'inter', 'tag', ' v1', ' v2', ' v3', ' v4', ' c,', ',c,', ',c']
                if any(marker in lower_line for marker in arrangement_markers):
                    # Additional check: if line has many commas relative to its length, it's likely arrangement info
                    comma_count = line.count(',')
                    if comma_count >= 3:  # Lines with 3+ commas are likely arrangement lines
                        continue
            
            # Skip common headers/footers (page numbers, URLs, copyright lines, etc.)
            lower_line = line.lower()
            
            # Skip lines that are just numbers (page numbers)
            if line.isdigit():
                continue
            
            # Skip URLs
            if "http" in lower_line or "www." in lower_line:
                continue
            
            # Skip copyright/licensing lines and admin lines
            if any(x in lower_line for x in ["copyright", "ccli", "license", "©", "®", "admin", "administered"]):
                continue
            
            # Skip very short lines that might be artifacts (less than 3 chars, unless it's a verse marker)
            if len(line) < 3 and not any(c.isalpha() for c in line):
                continue
            
            cleaned_lines.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        result = "\n".join(cleaned_lines)
        return result if result.strip() else None
        
    except Exception as exc:
        print(f"[WARN] Failed to extract lyrics from PDF for '{song_title}': {exc}")
        return None
