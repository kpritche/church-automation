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
from PyPDF2 import PdfReader, PdfWriter
from pypco.pco import PCO
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen.canvas import Canvas

REPO_ROOT = Path(__file__).resolve().parents[3]
BULLETINS_ROOT = Path(__file__).resolve().parents[2]
for p in (REPO_ROOT, BULLETINS_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from shared.paths import (
    BULLETINS_OUTPUT_DIR,
    BULLETINS_QR_DIR,
    FONT_SEARCH_PATHS as SHARED_FONT_PATHS,
    SLIDES_SLIDES_CONFIG,
)
from shared import config

CONFIG_PATH = os.getenv("SLIDES_CONFIG", str(SLIDES_SLIDES_CONFIG))
OUTPUT_DIR = BULLETINS_OUTPUT_DIR
QR_CODE_DIR = BULLETINS_QR_DIR

# Layout constants (points; letter size)
PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 pt
MARGIN_X = 30  # ~0.32 in
MARGIN_Y = 25
BODY_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)

# Spacing controls
SECTION_LEADING = 1.15
SUBHEADING_LEADING = 1.15
DESCRIPTION_LEADING = 1.15
BODY_LEADING = 1.2
BR_LINE_LEADING = 1.0    # per-line leading for <br>-separated text
PARAGRAPH_GAP = 8        # space after a paragraph (pt)
BR_GAP = 4               # gap after a <br>-separated line (pt)
ITEM_GAP = 10            # space after an item (pt)
DESCRIPTION_GAP = 6      # space after description (pt)
HEADING_GAP = 2          # gap after headings (pt)
BOLD_TAB_INDENT = 20     # indent (pt) applied to bold paragraphs
HEADER_BLOCK_PAD = 8     # padding above/below service header text inside colored bar
SERVICE_HEADER_OFFSET = 50 # increase to move header closer to the top

# Palette (brand set provided by user)
COLOR_BLACK = (0, 0, 0)
COLOR_PRIMARY = (0x16, 0x46, 0x3E)  # #16463e
COLOR_ACCENT = (0x51, 0xBF, 0x9B)  # #51bf9b
COLOR_TERTIARY = (0xFF, 0x7F, 0x30)  # #ff7f30
COLOR_HIGHLIGHT = (0x6F, 0xCF, 0xEB)  # #6fcfeb
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
        "SourceSansPro-SemiboldItalic.ttf",
        "SourceSansPro-SemiboldItalic.otf",
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
        self.title_name = self._register("bold", "SourceSansPro-Bold-28", 28)
        self.section_name = self._register("bold", "SourceSansPro-Bold-18", 18)
        self.subheading_name = self._register("bold", "SourceSansPro-Bold-16", 16)
        self.description_name = self._register("semibold", "SourceSansPro-Semibold-16", 16, allow_fallback=True)
        self.body_name = self._register("regular", "SourceSansPro-Regular-16", 16)
        self.body_bold_name = self._register("bold", "SourceSansPro-Bold-16", 16, allow_fallback=True)
        self.body_small_name = self._register("regular", "SourceSansPro-Regular-12", 12)
        # Sizes kept for layout calculations
        self.title_size = 28
        self.section_size = 18
        self.subheading_size = 16
        self.description_size = 16
        self.body_size = 16
        self.body_small_size = 12

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


def log_html_detail(title: str, html: str) -> None:
    if not html:
        return
    name = title or "(untitled)"
    print(f"[raw-html] item='{name}':\n{html}\n---")

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
    block_tags = {"p", "div", "li"}
    # Process only outermost block-level tags to avoid double counting nested blocks
    for node in soup.find_all(block_tags):
        if node.find_parent(block_tags):
            continue
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
                            paragraphs.append({
                                "text": f"{prefix}{line_text}",
                                "bold": line_bold,
                                "paragraph_end": False,
                                "break_kind": "br",
                            })
                    buffer = []
        if buffer:
            line_text = " ".join(t.strip() for t, _ in buffer if t.strip())
            line_bold = any(b for _, b in buffer)
            if line_text:
                prefix = "- " if node.name == "li" else ""
                paragraphs.append({
                    "text": f"{prefix}{line_text}",
                    "bold": line_bold,
                    "paragraph_end": True,
                    "break_kind": "p",
                })

    if not paragraphs:
        flat = soup.get_text("\n", strip=True)
        for ln in flat.split("\n"):
            if ln.strip():
                paragraphs.append({"text": ln.strip(), "bold": False, "break_kind": "p"})

    # Final cleanup: drop any empty paragraphs and trim whitespace
    cleaned: List[Dict[str, object]] = []
    for p in paragraphs:
        txt = (p.get("text") or "").strip()
        if txt:
            cleaned.append({
                "text": txt,
                "bold": bool(p.get("bold")),
                "paragraph_end": bool(p.get("paragraph_end")),
                "break_kind": p.get("break_kind", "p"),
            })

    # Drop consecutive duplicates that can arise from nested spans/line breaks
    deduped: List[Dict[str, object]] = []
    last_key: Optional[Tuple[str, bool, str]] = None
    for entry in cleaned:
        key = (entry.get("text", ""), bool(entry.get("bold")), entry.get("break_kind", "p"))
        if key == last_key:
            continue
        deduped.append(entry)
        last_key = key

    return deduped


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
        return att_id

    # 3) attachments link
    links = item_obj.get("links") or {}
    attach_url = links.get("attachments")
    if attach_url:
        resp = pco.get(attach_url)
        data = resp.get("data") or []
        if data:
            att_id = str(data[0].get("id"))
            return att_id
        else:
            print(f"[cover] no attachments returned for item {item_id} from link")
    else:
        print(f"[cover] no attachments link for item {item_id}")

    # 4) explicit endpoint fallback
    direct_url = (
        f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items/{item_id}/attachments"
    )
    resp = pco.get(direct_url)
    data = resp.get("data") or []
    if data:
        att_id = str(data[0].get("id"))
        return att_id
    return None


def download_attachment_image(attachment_id: str) -> Tuple[Optional[Image.Image], Optional[bytes]]:
    """Download the attachment binary.

    Returns (image, pdf_bytes). If the attachment is a PDF, image is None and pdf_bytes
    contains the raw PDF bytes (first page will be used as the cover). If the attachment
    is an image, pdf_bytes is None.
    """
    open_url = f"https://api.planningcenteronline.com/services/v2/attachments/{attachment_id}/open"
    print(f"[cover] requesting attachment open for {attachment_id} -> {open_url}")
    resp = requests.post(open_url, auth=HTTPBasicAuth(config.client_id, config.secret))
    resp.raise_for_status()

    attachment_url: Optional[str] = None
    try:
        data = resp.json()
        attachment_url = (
            data.get("data", {}).get("attributes", {}).get("attachment_url")
            or data.get("attachment_url")
        )
    except Exception:
        pass

    if not attachment_url and resp.headers.get("location"):
        attachment_url = resp.headers["location"]

    if not attachment_url:
        print(f"[WARN] Could not resolve attachment_url for {attachment_id}; response content: {resp.text[:200]}")
        return None, None

    file_resp = requests.get(attachment_url)
    file_resp.raise_for_status()
    content = file_resp.content
    if content[:4].upper() == b"%PDF":
        print(f"[cover] attachment {attachment_id} detected as PDF from resolved URL")
        return None, content
    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
        print(f"[cover] attachment {attachment_id} decoded as image size={img.size}")
        return img, None
    except Exception as exc:  # pragma: no cover
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
        # log_html_detail(title, html_detail)
        current_section["items"].append(
            {
                "title": title,
                "description": description,
                "html_paragraphs": parse_html_detail(html_detail),
                "is_song": is_song,
            }
        )

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

    def _set_cursor(self, value: float, note: str = "") -> None:
        self.cursor_y = float(value)

    def _bump_cursor(self, delta: float, note: str = "") -> None:
        self.cursor_y += float(delta)

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

    def draw_cover(self, cover: Optional[Image.Image], cover_pdf_bytes: Optional[bytes]) -> None:
        if cover_pdf_bytes:
            self.cover_pdf_bytes = cover_pdf_bytes
            return
        if cover is None:
            self.canvas.setFont(self.fonts.title_name, self.fonts.title_size)
            self.canvas.setFillColorRGB(0, 0, 0)
            self.canvas.drawString(MARGIN_X, PAGE_HEIGHT - MARGIN_Y - self.fonts.title_size, "Bulletin Cover Missing")
            self.canvas.showPage()
            self._set_cursor(MARGIN_Y)
            return
        img_w, img_h = cover.size
        scale = min(PAGE_WIDTH / img_w, PAGE_HEIGHT / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (PAGE_WIDTH - draw_w) / 2
        y = (PAGE_HEIGHT - draw_h) / 2
        self.canvas.drawImage(ImageReader(cover), x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
        self.canvas.showPage()
        self._set_cursor(MARGIN_Y)

    def add_cover(self, cover: Optional[Image.Image], cover_pdf_bytes: Optional[bytes]) -> None:
        self.draw_cover(cover, cover_pdf_bytes)

    def start_content(self) -> None:
        self._set_cursor(MARGIN_Y)

    def draw_service_header(self, service_name: str, plan_date: str) -> None:
        line = f"{service_name} - {format_human_date(plan_date)}"
        line_height = self._line_height(self.fonts.title_size, leading=1.15)
        block_height = line_height + (HEADER_BLOCK_PAD * 2)

        # Apply upward offset without changing margins
        header_cursor = max(0, self.cursor_y - SERVICE_HEADER_OFFSET)
        self._ensure_space(block_height)

        block_y = PAGE_HEIGHT - header_cursor - block_height
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_HIGHLIGHT))
        self.canvas.rect(0, block_y, PAGE_WIDTH, block_height, stroke=0, fill=1)

        line_width = self._measure(line, self.fonts.title_name, self.fonts.title_size)
        x = MARGIN_X + (BODY_WIDTH - line_width) / 2
        text_y = block_y + (block_height - self.fonts.title_size) / 2
        self.canvas.setFont(self.fonts.title_name, self.fonts.title_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
        self.canvas.drawString(x, text_y, line)

        self._set_cursor(header_cursor + block_height)
        self._bump_cursor(12)

    def draw_section_header(self, title: Optional[str]) -> None:
        if not title:
            return
        height = self._line_height(self.fonts.section_size)
        self._ensure_space(height + 8)
        line_width = self._measure(title, self.fonts.section_name, self.fonts.section_size)
        x = MARGIN_X + (BODY_WIDTH - line_width) / 2
        self.canvas.setFont(self.fonts.section_name, self.fonts.section_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_BLACK))
        self.canvas.drawString(x, PAGE_HEIGHT - self.cursor_y - self.fonts.section_size, title)
        self._bump_cursor(height)
        self._bump_cursor(8)

    def draw_wrapped_block(
        self,
        text: str,
        font_name: str,
        font_size: float,
        color: Tuple[int, int, int],
        align: str = "left",
        leading: float = 1.2,
        indent: float = 0.0,
    ) -> None:
        effective_width = BODY_WIDTH - indent
        lines = self._wrap(text, font_name, font_size, effective_width)
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
                x = MARGIN_X + indent
            self.canvas.drawString(x, PAGE_HEIGHT - self.cursor_y - font_size, line)
            self._bump_cursor(self._line_height(font_size, leading=leading))

    def draw_item(self, item: Dict[str, object]) -> None:
        title = item.get("title", "")
        description = item.get("description") or ""
        paragraphs = item.get("html_paragraphs") or []
        is_song = bool(item.get("is_song"))

        def estimate_height() -> float:
            h = 0.0
            if title:
                h += self._line_height(self.fonts.subheading_size, leading=1.15)
                h += HEADING_GAP
            if is_song and title:
                h += self._line_height(self.fonts.description_size, leading=DESCRIPTION_LEADING)
                h += HEADING_GAP
            if description:
                h += self._line_height(self.fonts.description_size, leading=DESCRIPTION_LEADING)
                h += DESCRIPTION_GAP
            for para in paragraphs:
                text = para.get("text", "")
                is_bold = bool(para.get("bold"))
                font_name = self.fonts.body_bold_name if is_bold else self.fonts.body_name
                break_kind = para.get("break_kind", "p")
                line_leading = BR_LINE_LEADING if break_kind == "br" else BODY_LEADING
                lines = self._wrap(text, font_name, self.fonts.body_size, BODY_WIDTH)
                if lines:
                    h += len(lines) * self._line_height(self.fonts.body_size, leading=line_leading)
                    if break_kind == "br":
                        h += BR_GAP
                    elif para.get("paragraph_end"):
                        h += PARAGRAPH_GAP
            h += ITEM_GAP
            return h

        total_height = estimate_height()
        if total_height > 0:
            available = (PAGE_HEIGHT - MARGIN_Y) - self.cursor_y
            if available / total_height < 0.2:
                self._new_page()

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
            self._bump_cursor(HEADING_GAP)

        if is_song and title:
            self.draw_wrapped_block(
                f"\"{title}\"",
                self.fonts.description_name,
                self.fonts.description_size,
                COLOR_PRIMARY,
                align="center",
                leading=1.15,
            )
            self._bump_cursor(HEADING_GAP)

        if description:
            self.draw_wrapped_block(
                description,
                self.fonts.description_name,
                self.fonts.description_size,
                COLOR_PRIMARY,
                align="center",
                leading=DESCRIPTION_LEADING,
            )
            self._bump_cursor(DESCRIPTION_GAP)

        for para in paragraphs:
            text = para.get("text", "")
            is_bold = bool(para.get("bold"))
            is_par_end = bool(para.get("paragraph_end"))
            break_kind = para.get("break_kind", "p")
            font_name = self.fonts.body_bold_name if is_bold else self.fonts.body_name
            indent = BOLD_TAB_INDENT if is_bold else 0.0
            self.draw_wrapped_block(
                text,
                font_name,
                self.fonts.body_size,
                COLOR_BLACK,
                align="left",
                leading=BR_LINE_LEADING if break_kind == "br" else BODY_LEADING,
                indent=indent,
            )
            if break_kind == "br":
                self._bump_cursor(BR_GAP)
            elif is_par_end:
                self._bump_cursor(PARAGRAPH_GAP)

        self._bump_cursor(ITEM_GAP)

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

    def _draw_list_in_columns(self, items: List[str], num_columns: int = 3) -> None:
        if not items:
            return

        col_width = BODY_WIDTH / num_columns
        # Ceiling division to calculate items per column
        items_per_column = (len(items) + num_columns - 1) // num_columns
        
        max_cursor_y = self.cursor_y
        original_cursor_y = self.cursor_y
        
        self.canvas.setFont(self.fonts.body_small_name, self.fonts.body_small_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_BLACK))

        for col_idx in range(num_columns):
            self._set_cursor(original_cursor_y)
            start_index = col_idx * items_per_column
            end_index = min(start_index + items_per_column, len(items))
            
            x = MARGIN_X + col_idx * col_width
            
            for i in range(start_index, end_index):
                item = items[i]
                # We need to check for space on each line to handle page breaks correctly inside columns
                self._ensure_space(self._line_height(self.fonts.body_small_size, leading=1.2))
                y = PAGE_HEIGHT - self.cursor_y - self.fonts.body_small_size
                self.canvas.drawString(x, y, item)
                self._bump_cursor(self._line_height(self.fonts.body_small_size, leading=1.2))
            
            max_cursor_y = max(max_cursor_y, self.cursor_y)
        
        self._set_cursor(max_cursor_y)

    def _draw_prayer_list(self, title: str, names: List[str], num_columns: int = 3) -> None:
        self.canvas.setFont(self.fonts.subheading_name, self.fonts.subheading_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
        
        # Center the title
        title_width = self._measure(title, self.fonts.subheading_name, self.fonts.subheading_size)
        x = MARGIN_X + (BODY_WIDTH - title_width) / 2
        
        self._ensure_space(self._line_height(self.fonts.subheading_size, leading=1.2) + 4)
        self.canvas.drawString(x, PAGE_HEIGHT - self.cursor_y - self.fonts.subheading_size, title)
        self._bump_cursor(self._line_height(self.fonts.subheading_size, leading=1.2))
        self._bump_cursor(4)  # padding after title

        self._draw_list_in_columns(names, num_columns=num_columns)
        self._bump_cursor(10)

    def _sort_positions(self, positions: List[str]) -> List[str]:
        """Sort positions with custom priority: Lead Pastor before Assistant Pastor, then alphabetically."""
        def sort_key(position: str) -> Tuple[int, str]:
            # Assign priority: lower numbers come first
            if "Lead Pastor" in position:
                return (0, position)
            elif "Assistant Pastor" in position:
                return (1, position)
            else:
                return (2, position)
        return sorted(positions, key=sort_key)

    def draw_prayers_and_worship_page(
        self,
        qr_codes: Dict[str, Optional[Image.Image]],
        worship_team: Dict[str, List[str]],
        position_to_team_map: Optional[Dict[str, str]] = None,
    ) -> None:
        self._new_page()
        
        # Prayers Section
        self.draw_section_header("Prayers")
        
        prayer_lists = {
            "Concerns Shared": ["Rene Reynoso, Cousin of Letty Mitchell", "WR Miller",
                                "Marissa Rowe, Niece of Barbara Krause", "Mace Williams",
                                "Emily Mclaughlin, Niece of Mary Maxine", "All in need of prayers"],
            "Those In Memory Care": ["Jack Gaunt", "Pat Staver"],
            "Our Military": ["CDR James Beaty", "SMAN Kevin Clute", "LTC Kevin Field",
                             "HM2 Kim Fountain", "AWR1 Isaiah Hale", "MSG Anthony Mauro",
                             "SMAN Ben Ridings", "LCDR Alex Turco", "TSGT Gerald Welker"],
        }
        
        for title, names in prayer_lists.items():
            # Use 2 columns for Concerns Shared, 3 for others
            num_cols = 2 if title == "Concerns Shared" else 3
            self._draw_prayer_list(title, names, num_columns=num_cols)
            
        # Worship Team Section
        self.draw_section_header("Worship Team")
        
        # Organize worship team by team from Planning Center
        if position_to_team_map:
            # Group positions by team from Planning Center
            team_groups: Dict[str, List[str]] = {}
            for position in worship_team.keys():
                team_name = position_to_team_map.get(position, "Other")
                if team_name not in team_groups:
                    team_groups[team_name] = []
                team_groups[team_name].append(position)
            
            # Sort teams for consistent display
            sorted_teams = sorted(team_groups.keys())
            num_teams = len(sorted_teams)
            
            if num_teams == 0:
                self._bump_cursor(20)
            else:
                # Draw teams in columns
                col_width = BODY_WIDTH / num_teams
                original_cursor_y = self.cursor_y
                max_cursor_y = self.cursor_y
                
                for col_idx, team_name in enumerate(sorted_teams):
                    # Reset cursor for each column
                    self.cursor_y = original_cursor_y
                    x_offset = MARGIN_X + (col_idx * col_width)
                    positions = self._sort_positions(team_groups[team_name])
                    
                    # Draw team name
                    self.canvas.setFont(self.fonts.body_bold_name, self.fonts.body_size)
                    self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
                    self.canvas.drawString(x_offset, PAGE_HEIGHT - self.cursor_y - self.fonts.body_size, team_name)
                    self._bump_cursor(self._line_height(self.fonts.body_size, leading=1.2))
                    self._bump_cursor(4)
                    
                    # Draw each position and its members
                    for position in positions:
                        members = worship_team.get(position, [])
                        if not members:
                            continue
                        
                        # Draw position as a small title
                        self.canvas.setFont(self.fonts.body_bold_name, self.fonts.body_small_size)
                        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_BLACK))
                        self.canvas.drawString(x_offset, PAGE_HEIGHT - self.cursor_y - self.fonts.body_small_size, position + ":")
                        self._bump_cursor(self._line_height(self.fonts.body_small_size, leading=1.2))
                        
                        # Draw member names
                        self.canvas.setFont(self.fonts.body_small_name, self.fonts.body_small_size)
                        for member in members:
                            self.canvas.drawString(x_offset + 10, PAGE_HEIGHT - self.cursor_y - self.fonts.body_small_size, member)
                            self._bump_cursor(self._line_height(self.fonts.body_small_size, leading=1.2))
                        
                        self._bump_cursor(4)  # spacing between positions
                    
                    # Track the tallest column
                    max_cursor_y = max(max_cursor_y, self.cursor_y)
                
                # Set cursor to the bottom of the tallest column
                self._set_cursor(max_cursor_y)
                self._bump_cursor(6)  # spacing after teams section
        else:
            # Fallback to hardcoded grouping if team info not available
            team_groups = {
                "Band": ["Drums", "Bass", "Guitar", "Keys", "Acoustic Guitar"],
                "Vocals": ["Vocals", "Worship Leader"],
                "Tech": ["Sound", "Lights", "Video", "Slides"],
                "Production": ["Production Director", "Stage Manager"],
            }
            
            # Filter to only teams that have members
            active_teams = {
                team_name: positions
                for team_name, positions in team_groups.items()
                if any(position in worship_team for position in positions)
            }
            
            num_teams = len(active_teams)
            if num_teams == 0:
                self._bump_cursor(20)
            else:
                # Draw teams in columns
                col_width = BODY_WIDTH / num_teams
                original_cursor_y = self.cursor_y
                max_cursor_y = self.cursor_y
                
                for col_idx, (team_name, positions) in enumerate(sorted(active_teams.items())):
                    # Reset cursor for each column
                    self.cursor_y = original_cursor_y
                    x_offset = MARGIN_X + (col_idx * col_width)
                    positions = self._sort_positions(positions)
                    
                    # Draw team name
                    self.canvas.setFont(self.fonts.body_bold_name, self.fonts.body_size)
                    self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_PRIMARY))
                    self.canvas.drawString(x_offset, PAGE_HEIGHT - self.cursor_y - self.fonts.body_size, team_name)
                    self._bump_cursor(self._line_height(self.fonts.body_size, leading=1.2))
                    self._bump_cursor(4)
                    
                    # Draw each position and its members
                    for position in positions:
                        if position not in worship_team:
                            continue
                            
                        members = worship_team[position]
                        if not members:
                            continue
                        
                        # Draw position as a small title
                        self.canvas.setFont(self.fonts.body_bold_name, self.fonts.body_small_size)
                        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_BLACK))
                        self.canvas.drawString(x_offset, PAGE_HEIGHT - self.cursor_y - self.fonts.body_small_size, position + ":")
                        self._bump_cursor(self._line_height(self.fonts.body_small_size, leading=1.2))
                        
                        # Draw member names
                        self.canvas.setFont(self.fonts.body_small_name, self.fonts.body_small_size)
                        for member in members:
                            self.canvas.drawString(x_offset + 10, PAGE_HEIGHT - self.cursor_y - self.fonts.body_small_size, member)
                            self._bump_cursor(self._line_height(self.fonts.body_small_size, leading=1.2))
                        
                        self._bump_cursor(4)  # spacing between positions
                    
                    # Track the tallest column
                    max_cursor_y = max(max_cursor_y, self.cursor_y)
                
                # Set cursor to the bottom of the tallest column
                self._set_cursor(max_cursor_y)
                self._bump_cursor(6)  # spacing after teams section
        
        self._bump_cursor(20)

        # QR Codes Section
        self.draw_section_header("Quick Links")
        
        qr_data = [
            ("Giving", "giving", "https://onrealm.org/FUMCWL/-/FORM/GIVE/NOW"),
            ("Bulletin", "bulletin", "https://www.fumcwl.org/BULLETINS/"),
            ("Check In", "check_in", "https://docs.google.com/forms/d/e/1FAIpQLScTj926IgaCzwhnaylcsMF0GOYgkCaYJzE4jSnt0IbmYr_B-w/viewform")
        ]
        
        qr_size = 130
        num_qrs = len(qr_data)
        col_width = BODY_WIDTH / num_qrs
        
        stagger_offsets = [0, 30, 0]

        # Find the max height of the staggered QR blocks to center them
        max_stagger = max(stagger_offsets)
        link_height = self.fonts.body_small_size + 5
        total_block_height = qr_size + max_stagger + link_height
        
        # Reserve space for footer text (2 lines + spacing)
        footer_height = 2 * self._line_height(self.fonts.body_small_size, leading=1.2) + 18
        
        available_height = PAGE_HEIGHT - self.cursor_y - MARGIN_Y - footer_height
        y_start = self.cursor_y + (available_height - total_block_height) / 2

        for idx, (label, key, url) in enumerate(qr_data):
            img = qr_codes.get(key)
            
            x = MARGIN_X + (col_width * idx) + (col_width - qr_size) / 2
            y = PAGE_HEIGHT - y_start - qr_size - stagger_offsets[idx]

            if img:
                self.canvas.drawImage(ImageReader(img), x, y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask="auto")
            else:
                self.canvas.rect(x, y, qr_size, qr_size, stroke=1, fill=0)
                self.canvas.drawString(x + 8, y + qr_size / 2, "Missing QR")
            
            self.canvas.linkURL(url, (x, y, x + qr_size, y + qr_size), relative=1)

            link_y = y - link_height
            
            self.canvas.setFont(self.fonts.body_small_name, self.fonts.body_small_size)
            self.canvas.setFillColorRGB(0, 0, 1) # Blue for link
            
            label_width = self._measure(label, self.fonts.body_small_name, self.fonts.body_small_size)
            label_x = x + (qr_size - label_width) / 2
            
            self.canvas.drawString(label_x, link_y, label)
            self.canvas.linkURL(url, (label_x, link_y, label_x + label_width, link_y + self.fonts.body_small_size), relative=1)
            self.canvas.line(label_x, link_y - 1, label_x + label_width, link_y - 1)

        # Footer text at bottom of page
        footer_lines = [
            "To be put on the weekly announcement emails, contact Ronda at 765-743-1285 or rkroeschen@fumcwl.org",
            "Copyright and licensing liturgy: Ministry Matters, www.umcdiscipleship.org, Music: CCLI 1218620; CCSWorshipCast 6802"
        ]
        
        self.canvas.setFont(self.fonts.body_small_name, self.fonts.body_small_size)
        self.canvas.setFillColorRGB(*(c / 255 for c in COLOR_BLACK))
        
        # Start from bottom margin and work upward
        footer_y = MARGIN_Y + (len(footer_lines) * self._line_height(self.fonts.body_small_size, leading=1.2))
        
        for idx, line in enumerate(reversed(footer_lines)):
            y_pos = MARGIN_Y + (idx * self._line_height(self.fonts.body_small_size, leading=1.2))
            # Center the text
            line_width = self._measure(line, self.fonts.body_small_name, self.fonts.body_small_size)
            x = MARGIN_X + (BODY_WIDTH - line_width) / 2
            self.canvas.drawString(x, y_pos, line)

        self.canvas.showPage()
        self._set_cursor(MARGIN_Y)

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


def fetch_team_members(pco: PCO, service_type_id: int, plan_id: str) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """
    Fetch team members and their positions from Planning Center.
    
    Returns:
        Tuple of (team_members_by_position, position_to_team_map)
        - team_members_by_position: Dict mapping position name to list of person names
        - position_to_team_map: Dict mapping position name to team name
    """
    team_members_by_position: Dict[str, List[str]] = {}
    position_to_team_map: Dict[str, str] = {}
    
    try:
        # Fetch all teams for this service type
        teams_resp = pco.get(f"/services/v2/service_types/{service_type_id}/teams")
        teams_by_id = {
            team["id"]: team["attributes"]["name"]
            for team in teams_resp.get("data", [])
        }
        
        # Fetch team members who have not declined (Confirmed or Unconfirmed)
        team_members_resp = pco.get(
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/team_members",
            params={"include": "person", "where[status]": "C,U"},
        )

        # Create a map for included people for easy lookup
        included_people = {
            inc["id"]: inc["attributes"]["name"]
            for inc in team_members_resp.get("included", [])
            if inc["type"] == "Person"
        }

        for member in team_members_resp.get("data", []):
            attrs = member.get("attributes", {})
            if attrs.get("status") in ("C", "U"):
                person_id = member["relationships"]["person"]["data"]["id"]
                person_name = included_people.get(person_id, attrs.get("name", "Unknown Person"))
                position_name = attrs.get("team_position_name", "Unknown Position")

                if position_name not in team_members_by_position:
                    team_members_by_position[position_name] = []
                team_members_by_position[position_name].append(person_name)
                
                # Get team name from relationships
                team_rel = member.get("relationships", {}).get("team", {}).get("data")
                if team_rel:
                    team_id = team_rel.get("id")
                    team_name = teams_by_id.get(team_id, "Other")
                    position_to_team_map[position_name] = team_name

    except Exception as e:
        print(f"Error fetching team members: {e}")

    return team_members_by_position, position_to_team_map


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

    worship_team, position_to_team_map = fetch_team_members(pco, service_type_id, plan_id)

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
    renderer.draw_prayers_and_worship_page(load_qr_codes(), worship_team, position_to_team_map)

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
