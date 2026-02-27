"""
Generate bulletin PDFs for each Planning Center service type in the next 7 days.

Rules (per user):
* Cover page: single image attachment on the "Bulletin Cover" item (first attachment if multiple).
* Section headers: Planning Center header items.
* Sub-headings: every other item title.
* Description: centered under the sub-heading.
* HTML detail: printed beneath, left-aligned, preserving basic formatting; ignore highlighted text.
* Fonts: Source Sans Pro family.
* Brand colors allowed: #000000, #16463e, #51bf9b, #ff7f30, #6fcfeb, #cda787, #ffffff.
* QR codes: bulletin/qr_codes (giving, bulletin, check in) printed three across on the last page.
* Output: bulletins/output/Bulletin-YYYY-MM-DD-<ServiceName>.pdf
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from requests.auth import HTTPBasicAuth
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypco.pco import PCO
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen.canvas import Canvas

from church_automation_shared.paths import (
    BULLETINS_OUTPUT_DIR,
    BULLETINS_QR_DIR,
    FONT_SEARCH_PATHS as SHARED_FONT_PATHS,
    SLIDES_SLIDES_CONFIG,
)
from church_automation_shared import config

CONFIG_PATH = os.getenv("SLIDES_CONFIG", str(SLIDES_SLIDES_CONFIG))
OUTPUT_DIR = BULLETINS_OUTPUT_DIR
QR_CODE_DIR = BULLETINS_QR_DIR

# Layout constants (points; letter size)
PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 pt
MARGIN_X = 46  # ~0.64 in
MARGIN_Y = 46
BODY_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)

# Palette (brand set provided by user)
COLOR_BLACK = (0, 0, 0)
COLOR_PRIMARY = (0x16, 0x46, 0x3E)  # #16463e
COLOR_ACCENT = (0x51, 0xBF, 0x9B)  # #51bf9b
COLOR_MUTED = (0xCD, 0xA7, 0x87)  # #cda787


FONT_FILES = {
    "regular": [
        "SourceSansPro-Regular.ttf",
        "SourceSansPro-Regular.otf",
    ],
    "semibold": [
        "SourceSansPro-Semibold.ttf",
        "SourceSansPro-Semibold.otf",
    ],
    "bold": [
        "SourceSansPro-Bold.ttf",
        "SourceSansPro-Bold.otf",
    ],
    "italic": [
        "SourceSansPro-It.ttf",
        "SourceSansPro-Italic.ttf",
        "SourceSansPro-RegularIt.ttf",
    ],
    "semibold_italic": [
        "SourceSansPro-SemiboldIt.ttf",
        "SourceSansPro-SemiboldIt.ttf",
    ],
}

FONT_SEARCH_PATHS = list(SHARED_FONT_PATHS)


def find_font_file(options: List[str]) -> Optional[Path]:
    for base in FONT_SEARCH_PATHS:
        for name in options:
            candidate = base / name
            if candidate.exists():
                return candidate
    return None


def is_preservice_item(attrs: Dict[str, object]) -> bool:
    """
    Heuristic to detect pre-service items from Planning Center item attributes.

    Planning Center exposes a `service_position` attribute on plan items; it is
    typically one of: "preservice", "service", or "postservice". We treat any
    value that starts with "pre" as a pre-service item. If this attribute is
    missing, we also honor a legacy/custom boolean `is_preservice` flag if
    present.
    """
    svc_pos = str(attrs.get("service_position", "") or "").strip().lower()
    if svc_pos.startswith("pre"):
        return True
    return bool(attrs.get("is_preservice"))


class FontBundle:
    """Holds the Source Sans Pro font faces used for rendering."""

    def __init__(self) -> None:
        self.title_name = self._register("bold", "SourceSansPro-Bold-26", 26)
        self.section_name = self._register("bold", "SourceSansPro-Bold-18", 18)
        self.subheading_name = self._register("semibold", "SourceSansPro-Semibold-16", 16)
        self.description_name = self._register("italic", "SourceSansPro-Italic-14", 14, allow_fallback=True)
        self.body_name = self._register("regular", "SourceSansPro-Regular-14", 14)
        self.body_bold_name = self._register("bold", "SourceSansPro-Bold-14", 14, allow_fallback=True)
        # Sizes kept for layout calculations
        self.title_size = 26
        self.section_size = 18
        self.subheading_size = 16
        self.description_size = 14
        self.body_size = 14

    def _register(self, weight_key: str, face_name: str, pt_size: int, allow_fallback: bool = False) -> str:
        path = find_font_file(FONT_FILES[weight_key])
        if not path:
            if allow_fallback:
                print(
                    f"[WARN] Missing Source Sans Pro font for '{weight_key}'. "
                    "Falling back to built-in Helvetica; please drop SourceSansPro .ttf/.otf files into assets/fonts."
                )
                return "Helvetica"
            raise FileNotFoundError(
                f"Source Sans Pro font file not found for '{weight_key}'. "
                "Place the font .ttf/.otf files in assets/fonts or install system-wide."
            )
        try:
            pdfmetrics.registerFont(TTFont(face_name, str(path)))
            return face_name
        except TTFError as exc:
            print(
                f"[WARN] Failed to register font {path} ({exc}); "
                "falling back to Helvetica. Please install TTF versions of Source Sans Pro in assets/fonts."
            )
            return "Helvetica"


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_next_seven_day_window() -> Tuple[str, str]:
    today = date.today()
    end = today + timedelta(days=7)
    return today.isoformat(), end.isoformat()


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "service"


def format_human_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %-d, %Y")
    except ValueError:
        # Windows does not support %-d; fallback to %#d
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %#d, %Y")


def remove_highlighted_text(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["mark"]):
        tag.decompose()
    for span in soup.find_all("span"):
        style = (span.get("style") or "").lower()
        cls = " ".join(span.get("class") or []).lower()
        if "background" in style or "highlight" in style or "marker" in cls:
            span.decompose()

def remove_red_text(soup: BeautifulSoup) -> None:
    def is_red_style(style: str) -> bool:
        return bool(
            re.search(
                r"color\s*:\s*(red|#f00\b|#ff0000\b|#ff0000ff\b|rgba?\s*\(\s*255\s*,\s*0\s*,\s*0(?:\s*,\s*[0-9.]+)?\s*\))",
                style,
                re.IGNORECASE,
            )
        )
    for tag in soup.find_all(True):
        style = (tag.get("style") or "")
        color_attr = (tag.get("color") or "")
        if is_red_style(style) or re.search(r"^red$", color_attr, re.IGNORECASE):
            tag.decompose()

def parse_html_detail(html: str) -> List[Dict[str, object]]:
    """Return a list of paragraphs with basic style flags from html_detail."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    remove_highlighted_text(soup)
    remove_red_text(soup)

    def iter_text_with_style(node: Tag, bold: bool = False):
        for child in node.children:
            if isinstance(child, NavigableString):
                yield str(child), bold
            elif isinstance(child, Tag):
                name = child.name.lower()
                if name == "br":
                    yield "\n", bold
                else:
                    child_bold = bold or name in {"strong", "b"}
                    yield from iter_text_with_style(child, child_bold)

    paragraphs: List[Dict[str, object]] = []
    # Process block-level tags in document order
    for node in soup.find_all(["p", "div", "li"]):
        pieces = list(iter_text_with_style(node))
        buffer: List[Tuple[str, bool]] = []
        for text, is_bold in pieces:
            parts = text.split("\n")
            for idx, part in enumerate(parts):
                if part:
                    buffer.append((part, is_bold))
                if idx < len(parts) - 1:
                    if buffer:
                        line_text = " ".join(t.strip() for t, _ in buffer if t.strip())
                        line_bold = any(b for _, b in buffer)
                        if line_text:
                            prefix = "- " if node.name == "li" else ""
                            paragraphs.append({"text": f"{prefix}{line_text}", "bold": line_bold, "paragraph_end": False})
                    buffer = []
        if buffer:
            line_text = " ".join(t.strip() for t, _ in buffer if t.strip())
            line_bold = any(b for _, b in buffer)
            if line_text:
                prefix = "- " if node.name == "li" else ""
                paragraphs.append({"text": f"{prefix}{line_text}", "bold": line_bold, "paragraph_end": True})

    if not paragraphs:
        flat = soup.get_text("\n", strip=True)
        for ln in flat.split("\n"):
            if ln.strip():
                paragraphs.append({"text": ln.strip(), "bold": False})

    # Final cleanup: drop any empty paragraphs and trim whitespace
    cleaned: List[Dict[str, object]] = []
    for p in paragraphs:
        txt = (p.get("text") or "").strip()
        if txt:
            cleaned.append({"text": txt, "bold": bool(p.get("bold"))})
    return cleaned


def fetch_first_attachment_id(
    pco: PCO,
    item_obj: Dict[str, object],
    service_type_id: int,
    plan_id: str,
    included: Optional[List[Dict[str, object]]] = None,
) -> Optional[str]:
    """
    Retrieve the first attachment id for an item, trying several sources:
      1) included attachments (when available in the API response)
      2) relationships->attachments->data from the item payload
      3) the attachments link on the item
    """
    item_id = str(item_obj.get("id", ""))
    # 1) included attachments
    if included:
        for inc in included:
            if inc.get("type") != "Attachment":
                continue
            rel = inc.get("relationships") or {}
            attachable = (rel.get("attachable") or {}).get("data") or {}
            if str(attachable.get("id")) == item_id:
                att_id = str(inc.get("id"))
                print(f"[cover] found attachment in included for item {item_id}: {att_id}")
                return att_id

    # 2) relationships data
    rel = (item_obj.get("relationships") or {}).get("attachments", {})
    data = rel.get("data") or []
    if data:
        att_id = str(data[0].get("id"))
        #print(f"[cover] found attachment in relationships for item {item_id}: {att_id}")
        return att_id

    # 3) attachments link
    links = item_obj.get("links") or {}
    attach_url = links.get("attachments")
    if attach_url:
        #print(f"[cover] fetching attachments via link for item {item_id}: {attach_url}")
        resp = pco.get(attach_url)
        data = resp.get("data") or []
        if data:
            att_id = str(data[0].get("id"))
            #print(f"[cover] found attachment via link for item {item_id}: {att_id}")
            return att_id
        else:
            print(f"[cover] no attachments returned for item {item_id} from link")
    else:
        print(f"[cover] no attachments link for item {item_id}")

    # 4) explicit endpoint fallback
    direct_url = (
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
    )
    #print(f"[cover] trying direct attachments endpoint for item {item_id}: {direct_url}")
    resp = pco.get(direct_url)
    data = resp.get("data") or []
    if data:
        att_id = str(data[0].get("id"))
        #print(f"[cover] found attachment via direct endpoint for item {item_id}: {att_id}")
        return att_id
    #print(f"[cover] no attachments found via direct endpoint for item {item_id}")

    return None


def download_attachment_image(attachment_id: str) -> Tuple[Optional[Image.Image], Optional[bytes]]:
    """Download the attachment binary.

    Returns (image, pdf_bytes). If the attachment is a PDF, image is None and pdf_bytes
    contains the raw PDF bytes (first page will be used as the cover). If the attachment
    is an image, pdf_bytes is None.
    """
    open_url = f"https://api.planningcenteronline.com/services/v2/attachments/{attachment_id}/open"
    print(f"[cover] requesting attachment open for {attachment_id} -> {open_url}")
    # Per Planning Center docs, this must be a POST to get the signed URL
    resp = requests.post(open_url, auth=HTTPBasicAuth(config.client_id, config.secret))
    resp.raise_for_status()

    attachment_url: Optional[str] = None
    # Try JSON body
    try:
        data = resp.json()
        attachment_url = (
            data.get("data", {}).get("attributes", {}).get("attachment_url")
            or data.get("attachment_url")
        )
        # if attachment_url:
        #     print(f"[cover] resolved attachment_url for {attachment_id}: {attachment_url}")
    except Exception:
        pass

    # Fallback: redirect Location header
    if not attachment_url and resp.headers.get("location"):
        attachment_url = resp.headers["location"]
        #print(f"[cover] resolved via Location header for {attachment_id}: {attachment_url}")

    if not attachment_url:
        print(f"[WARN] Could not resolve attachment_url for {attachment_id}; response content: {resp.text[:200]}")
        return None, None

    file_resp = requests.get(attachment_url)
    file_resp.raise_for_status()
    content = file_resp.content
    # PDF cover handling
    if content[:4].upper() == b"%PDF":
        print(f"[cover] attachment {attachment_id} detected as PDF from resolved URL")
        return None, content
    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
        print(f"[cover] attachment {attachment_id} decoded as image size={img.size}")
        return img, None
    except Exception as exc:  # pragma: no cover - depends on remote content
        print(f"[WARN] Failed to decode cover image attachment {attachment_id}: {exc}")
        return None, None


def load_qr_codes() -> Dict[str, Optional[Image.Image]]:
    codes = {}
    for key, filename in {
        "giving": "giving_link.png",
        "bulletin": "bulletin.png",
        "check_in": "check_in_form.png",
    }.items():
        path = QR_CODE_DIR / filename
        if path.exists():
            try:
                codes[key] = Image.open(path).convert("RGB")
            except Exception as exc:
                print(f"[WARN] Unable to open QR code {path}: {exc}")
                codes[key] = None
        else:
            print(f"[WARN] Missing QR code file: {path}")
            codes[key] = None
    return codes


def build_sections(
    items: List[Dict[str, object]],
    pco: PCO,
    included: Optional[List[Dict[str, object]]] = None,
    service_type_id: Optional[int] = None,
    plan_id: Optional[str] = None,
) -> Tuple[List[Dict[str, object]], Optional[str]]:
    """Create ordered sections/items and locate the cover attachment."""
    sections: List[Dict[str, object]] = []
    current_section: Optional[Dict[str, object]] = None
    cover_attachment_id: Optional[str] = None
    

    for item_obj in items:
        attrs = item_obj.get("attributes") or {}
        title = (attrs.get("title") or attrs.get("display_name") or "").strip()
        item_type = (attrs.get("item_type") or "").lower()
        is_preservice = is_preservice_item(attrs)
        is_song = item_type == "song"

        # Capture cover
        if title == "Bulletin Cover":
            try:
                cover_attachment_id = cover_attachment_id or fetch_first_attachment_id(
                    pco, item_obj, service_type_id=service_type_id or 0, plan_id=plan_id or "", included=included
                )
            except Exception as exc:
                print(f"[WARN] Unable to fetch cover attachment for item '{title}': {exc}")
            continue

        # Skip preservice items entirely
        if is_preservice:
            continue

        if item_type == "header":
            current_section = {"title": title, "items": []}
            sections.append(current_section)
            continue

        if current_section is None:
            current_section = {"title": None, "items": []}
            sections.append(current_section)

        description = (attrs.get("description") or "").strip()
        html_detail = attrs.get("html_details") or ""
        current_section["items"].append(
            {
                "title": title,
                "description": description,
                "html_paragraphs": parse_html_detail(html_detail),
                "is_song": is_song,
            }
        )

    # Drop empty leading section if it has no items
    sections = [s for s in sections if s.get("items")]
    return sections, cover_attachment_id


class BulletinRenderer:
    def __init__(self, fonts: FontBundle) -> None:
        self.fonts = fonts
        self.buffer = io.BytesIO()
        self.canvas = Canvas(self.buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
        self.cursor_y: float = MARGIN_Y
        self.current_item: Optional[str] = None
        self.cover_pdf_bytes: Optional[bytes] = None
        print(f"[cursor][-] init -> {self.cursor_y}")

    def _set_cursor(self, value: float, note: str = "") -> None:
        self.cursor_y = float(value)
        item_label = self.current_item or "-"
        msg = f"[cursor][{item_label}] set {self.cursor_y:.2f}"
        if note:
            msg += f" ({note})"
        # print(msg)

    def _bump_cursor(self, delta: float, note: str = "") -> None:
        self.cursor_y += float(delta)
        item_label = self.current_item or "-"
        msg = f"[cursor][{item_label}] +{delta} -> {self.cursor_y:.2f}"
        if note:
            msg += f" ({note})"
        # print(msg)

    # --- basic drawing helpers -------------------------------------------------
    def _new_page(self) -> None:
        self.canvas.showPage()
        self._set_cursor(MARGIN_Y, "new page start")

    def _ensure_space(self, needed_height: float) -> None:
        if self.cursor_y + needed_height <= PAGE_HEIGHT - MARGIN_Y:
            return
        self._new_page()

    def _line_height(self, size: float, leading: float = 1.2) -> float:
        return size * leading

    def _measure(self, text: str, font_name: str, size: float) -> float:
        return pdfmetrics.stringWidth(text, font_name, size)

    def _wrap(self, text: str, font_name: str, size: float, width: float) -> List[str]:
        if not text:
            return []
        words = text.split()
        if not words:
            return []
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            test = f"{current} {word}"
            if self._measure(test, font_name, size) <= width:
                current = test
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    # --- high-level drawing ----------------------------------------------------
    def draw_cover(self, cover: Optional[Image.Image], cover_pdf_bytes: Optional[bytes]) -> None:
        if cover_pdf_bytes:
            self.cover_pdf_bytes = cover_pdf_bytes
            return
        if cover is None:
            self.canvas.setFont(self.fonts.title_name, self.fonts.title_size)
            self.canvas.setFillColorRGB(0, 0, 0)
            self.canvas.drawString(MARGIN_X, PAGE_HEIGHT - MARGIN_Y - self.fonts.title_size, "Bulletin Cover Missing")
            self.canvas.showPage()
            self._set_cursor(MARGIN_Y, "after placeholder cover")
            return
        img_w, img_h = cover.size
        scale = min(PAGE_WIDTH / img_w, PAGE_HEIGHT / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (PAGE_WIDTH - draw_w) / 2
        y = (PAGE_HEIGHT - draw_h) / 2
        self.canvas.drawImage(ImageReader(cover), x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
        self.canvas.showPage()
        self._set_cursor(MARGIN_Y, "after cover image")

    # Backward-compatible wrapper
    def add_cover(self, cover: Optional[Image.Image], cover_pdf_bytes: Optional[bytes]) -> None:
        self.draw_cover(cover, cover_pdf_bytes)

    def start_content(self) -> None:
        self._set_cursor(MARGIN_Y, "content start")

    def draw_service_header(self, service_name: str, plan_date: str) -> None:
        line = f"{service_name} - {format_human_date(plan_date)}"
        self._ensure_space(self._line_height(self.fonts.title_size))
        line_width = self._measure(line, self.fonts.title_name, self.fonts.title_size)
        x = MARGIN_X + (BODY_WIDTH - line_width) / 2
        self.canvas.setFont(self.fonts.title_name, self.fonts.title_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
        self.canvas.drawString(x, PAGE_HEIGHT - self.cursor_y - self.fonts.title_size, line)
        self._bump_cursor(self._line_height(self.fonts.title_size, leading=1.15), "after service header")
        self._bump_cursor(12, "service header spacer")

    def draw_section_header(self, title: Optional[str]) -> None:
        if not title:
            return
        height = self._line_height(self.fonts.section_size)
        self._ensure_space(height + 8)
        line_width = self._measure(title, self.fonts.section_name, self.fonts.section_size)
        x = MARGIN_X + (BODY_WIDTH - line_width) / 2
        self.canvas.setFont(self.fonts.section_name, self.fonts.section_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
        self.canvas.drawString(x, PAGE_HEIGHT - self.cursor_y - self.fonts.section_size, title)
        self._bump_cursor(height, "after section header")
        self._bump_cursor(8, "section spacer")

    def draw_wrapped_block(
        self,
        text: str,
        font_name: str,
        font_size: float,
        color: Tuple[int, int, int],
        align: str = "left",
        leading: float = 1.2,
    ) -> None:
        lines = self._wrap(text, font_name, font_size, BODY_WIDTH)
        if not lines:
            return
        block_height = len(lines) * self._line_height(font_size, leading=leading)
        self._ensure_space(block_height)

        self.canvas.setFont(font_name, font_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in color))
        for line in lines:
            line_width = self._measure(line, font_name, font_size)
            if align == "center":
                x = MARGIN_X + (BODY_WIDTH - line_width) / 2
            else:
                x = MARGIN_X
            self.canvas.drawString(x, PAGE_HEIGHT - self.cursor_y - font_size, line)
            self._bump_cursor(self._line_height(font_size, leading=leading), "wrapped line")

    def draw_item(self, item: Dict[str, object]) -> None:
        title = item.get("title", "")
        description = item.get("description") or ""
        paragraphs = item.get("html_paragraphs") or []
        is_song = bool(item.get("is_song"))

        # Preflight height calculation to decide if we should start on a new page
        def estimate_height() -> float:
            h = 0.0
            if title:
                h += self._line_height(self.fonts.subheading_size, leading=1.15)
                h += 2
            if is_song and title:
                h += self._line_height(self.fonts.description_size, leading=1.15)
                h += 2
            if description:
                h += self._line_height(self.fonts.description_size, leading=1.15)
                h += 6
            for para in paragraphs:
                text = para.get("text", "")
                is_bold = bool(para.get("bold"))
                font_name = self.fonts.body_bold_name if is_bold else self.fonts.body_name
                lines = self._wrap(text, font_name, self.fonts.body_size, BODY_WIDTH)
                if lines:
                    h += len(lines) * self._line_height(self.fonts.body_size, leading=1.15)
                    h += 6
            h += 8  # after item spacer
            return h

        total_height = estimate_height()
        if total_height > 0:
            available = (PAGE_HEIGHT - MARGIN_Y) - self.cursor_y
            if available / total_height < 0.2:
                self._new_page()

        # Sub-heading
        if title:
            self.current_item = title or "(untitled)"
            heading_text = "Song" if is_song else str(title)
            self.draw_wrapped_block(
                heading_text,
                self.fonts.subheading_name,
                self.fonts.subheading_size,
                COLOR_ACCENT,
                align="center",
                leading=1.15,
            )
            self._bump_cursor(4, "subheading spacer")

        # For songs, show the song title beneath the heading using description styling
        if is_song and title:
            self.draw_wrapped_block(
                f"\"{title}\"",
                self.fonts.description_name,
                self.fonts.description_size,
                COLOR_PRIMARY,
                align="center",
                leading=1.15,
            )
            self._bump_cursor(4, "song title spacer")

        # Centered description (plain text)
        if description:
            self.draw_wrapped_block(
                description,
                self.fonts.description_name,
                self.fonts.description_size,
                COLOR_PRIMARY,
                align="center",
                leading=1.15,
            )
            self._bump_cursor(6, "description spacer")

        # HTML detail paragraphs
        for para in paragraphs:
            text = para.get("text", "")
            is_bold = bool(para.get("bold"))
            is_par_end = bool(para.get("paragraph_end"))
            font_name = self.fonts.body_bold_name if is_bold else self.fonts.body_name
            self.draw_wrapped_block(
                text,
                font_name,
                self.fonts.body_size,
                COLOR_BLACK,
                align="left",
                leading=1.15,
            )
            if is_par_end:
                self._bump_cursor(6, "paragraph spacer")

        # Space after item
        self._bump_cursor(10, "after item")

    def draw_sections(self, sections: List[Dict[str, object]], service_name: str, plan_date: str) -> None:
        self.start_content()
        self.draw_service_header(service_name, plan_date)
        for section in sections:
            items = section.get("items", [])
            if items:
                reserve = (
                    self._line_height(self.fonts.section_size, leading=1.1)
                    + 6
                    + self._line_height(self.fonts.subheading_size, leading=1.1)
                    + 6
                )
                self._ensure_space(reserve)
            self.draw_section_header(section.get("title"))
            for item in items:
                self.draw_item(item)

    def draw_qr_page(self, qr_codes: Dict[str, Optional[Image.Image]]) -> None:
        self._new_page()
        # Title
        self.canvas.setFont(self.fonts.section_name, self.fonts.section_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
        self.canvas.drawString(MARGIN_X, PAGE_HEIGHT - self.cursor_y - self.fonts.section_size, "Quick Links")
        self._bump_cursor(self._line_height(self.fonts.section_size, leading=1.25), "qr title spacer")
        self._bump_cursor(14, "qr block spacer")

        labels = [("Giving", "giving"), ("Bulletin", "bulletin"), ("Check In", "check_in")]
        usable_width = BODY_WIDTH
        gutter = 18
        qr_size = (usable_width - (gutter * 2)) / 3

        for idx, (label, key) in enumerate(labels):
            img = qr_codes.get(key)
            x = MARGIN_X + idx * (qr_size + gutter)
            y = PAGE_HEIGHT - self.cursor_y - qr_size

            self.canvas.setFont(self.fonts.subheading_name, self.fonts.subheading_size)
            self.canvas.setFillColorRGB(0, 0, 0)
            self.canvas.drawString(x, y + qr_size + self.fonts.subheading_size + 4, label)

            if img:
                self.canvas.drawImage(ImageReader(img), x, y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask="auto")
            else:
                self.canvas.rect(x, y, qr_size, qr_size, stroke=1, fill=0)
                self.canvas.drawString(x + 8, y + qr_size / 2, "Missing QR")

        self.canvas.showPage()
        self._set_cursor(MARGIN_Y, "after qr page")

    def save(self, path: Path) -> None:
        self.canvas.save()
        path.parent.mkdir(parents=True, exist_ok=True)

        generated_reader = PdfReader(io.BytesIO(self.buffer.getvalue()))
        writer = PdfWriter()

        if self.cover_pdf_bytes:
            cover_reader = PdfReader(io.BytesIO(self.cover_pdf_bytes))
            if cover_reader.pages:
                writer.add_page(cover_reader.pages[0])

        for page in generated_reader.pages:
            writer.add_page(page)

        with open(path, "wb") as f:
            writer.write(f)


def fetch_service_name(pco: PCO, service_type_id: int) -> str:
    resp = pco.get(f"/services/v2/service_types/{service_type_id}")
    return resp["data"]["attributes"]["name"]


def find_plans_in_range(pco: PCO, service_type_id: int, start_date: str, end_date: str) -> List[Dict[str, object]]:
    plans = pco.iterate(f"/services/v2/service_types/{service_type_id}/plans", filter="future")
    selected: List[Dict[str, object]] = []
    for plan_obj in plans:
        sort_date = plan_obj["data"]["attributes"].get("sort_date", "")
        plan_date = sort_date[:10] if sort_date else ""
        if plan_date and start_date <= plan_date <= end_date:
            selected.append({"plan": plan_obj, "plan_date": plan_date})
    return selected


def process_plan(pco: PCO, service_type_id: int, plan_id: str, plan_date: str, service_name: str) -> None:
    items_resp = pco.get(
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items",
        include="attachments",
    )
    items = items_resp.get("data", [])

    sections, cover_attachment_id = build_sections(
        items,
        pco,
        items_resp.get("included"),
        service_type_id=service_type_id,
        plan_id=plan_id,
    )
    if not sections:
        print(f"[INFO] No items with html/description found for plan {plan_id} ({plan_date}); skipping.")
        return

    cover_img: Optional[Image.Image] = None
    cover_pdf_bytes: Optional[bytes] = None
    if cover_attachment_id:
        cover_img, cover_pdf_bytes = download_attachment_image(cover_attachment_id)
    else:
        print(f"[WARN] No cover attachment found for plan {plan_id}.")

    fonts = FontBundle()
    renderer = BulletinRenderer(fonts)
    renderer.add_cover(cover_img, cover_pdf_bytes)
    renderer.draw_sections(sections, service_name, plan_date)
    renderer.draw_qr_page(load_qr_codes())

    safe_service = safe_slug(service_name)
    filename = f"Bulletin-{plan_date}-{safe_service}.pdf"
    output_path = OUTPUT_DIR / filename
    renderer.save(output_path)
    print(f"[OK] Bulletin saved to {output_path}")


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    service_type_ids = cfg.get("service_type_ids", [])
    if not service_type_ids:
        raise ValueError("No service_type_ids configured in slides_config.json")

    start_date, end_date = get_next_seven_day_window()
    print(f"Generating bulletins for plans between {start_date} and {end_date}")

    pco = PCO(application_id=config.client_id, secret=config.secret)

    for stid in service_type_ids:
        service_name = fetch_service_name(pco, stid)
        plans = find_plans_in_range(pco, stid, start_date, end_date)
        if not plans:
            print(f"[INFO] No plans for service type {stid} ({service_name}) in window; skipping.")
            continue

        for entry in plans:
            plan_obj = entry["plan"]
            plan_date = entry["plan_date"]
            plan_id = plan_obj["data"]["id"]
            print(f"[INFO] Processing plan {plan_id} ({service_name}) on {plan_date}")
            process_plan(pco, stid, plan_id, plan_date, service_name)


if __name__ == "__main__":
    main()
