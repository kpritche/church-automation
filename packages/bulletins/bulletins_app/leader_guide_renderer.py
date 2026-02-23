"""
Service Leader Guide PDF renderer.

Renders service items (title, description, html_details) into a PDF document
suitable for service leaders during worship. Includes attachments (lyrics, sheet music)
embedded after their corresponding items with clear separators.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen.canvas import Canvas
from PyPDF2 import PdfReader, PdfWriter

try:
    from church_automation_shared.paths import (
        FONT_SEARCH_PATHS as SHARED_FONT_PATHS,
    )
except ModuleNotFoundError:
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared.paths import (
        FONT_SEARCH_PATHS as SHARED_FONT_PATHS,
    )


# Page layout constants (points; letter size)
PAGE_WIDTH, PAGE_HEIGHT = letter  # 612 x 792 pt
MARGIN_X = 30
MARGIN_Y = 25
BODY_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)

# Font files
FONT_FILES = {
    "regular": [
        "SourceSansPro-Regular.ttf",
        "SourceSansPro-Regular.otf",
    ],
    "bold": [
        "SourceSansPro-Bold.ttf",
        "SourceSansPro-Bold.otf",
    ],
}

FONT_SEARCH_PATHS = list(SHARED_FONT_PATHS)


def find_font_file(options: List[str]) -> Optional[Path]:
    """Find font file from search paths."""
    for base in FONT_SEARCH_PATHS:
        for name in options:
            candidate = base / name
            if candidate.exists():
                return candidate
    return None


class FontBundle:
    """Holds registered fonts for the leader guide."""

    def __init__(self) -> None:
        self.title_name = self._register("bold", "SourceSansPro-Bold-24", 24)
        self.heading_name = self._register("bold", "SourceSansPro-Bold-14", 14)
        self.body_name = self._register("regular", "SourceSansPro-Regular-12", 12)
        self.small_name = self._register("regular", "SourceSansPro-Regular-10", 10)

        self.title_size = 24
        self.heading_size = 14
        self.body_size = 12
        self.small_size = 10

    def _register(self, weight_key: str, face_name: str, pt_size: int) -> str:
        path = find_font_file(FONT_FILES[weight_key])
        if not path:
            # Fallback to Helvetica if font not found
            return "Helvetica"
        try:
            pdfmetrics.registerFont(TTFont(face_name, str(path)))
            return face_name
        except TTFError:
            return "Helvetica"


class LeaderGuideRenderer:
    """Renders service items and attachments into a leader guide PDF."""

    def __init__(self) -> None:
        self.fonts = FontBundle()
        self.sections: List[Tuple[str, bytes]] = []  # List of ('canvas', bytes) or ('attachment', bytes)
        self.current_buffer = io.BytesIO()
        self.canvas = Canvas(self.current_buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
        self.cursor_y: float = MARGIN_Y

    def _finalize_canvas(self) -> None:
        """Save current canvas content and start a new one."""
        if self.cursor_y > MARGIN_Y:  # Only save if we drew something
            self.canvas.save()
            self.sections.append(('canvas', self.current_buffer.getvalue()))
        
        # Start new canvas for next section
        self.current_buffer = io.BytesIO()
        self.canvas = Canvas(self.current_buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
        self.cursor_y = MARGIN_Y

    def _new_page(self) -> None:
        """Create a new page and reset cursor."""
        self.canvas.showPage()
        self.cursor_y = MARGIN_Y

    def _ensure_space(self, needed_height: float) -> None:
        """Create new page if not enough space."""
        if self.cursor_y + needed_height <= PAGE_HEIGHT - MARGIN_Y:
            return
        self._new_page()

    def _measure(self, text: str, font_name: str, size: float) -> float:
        """Measure text width."""
        return pdfmetrics.stringWidth(text, font_name, size)

    def _wrap(self, text: str, font_name: str, size: float, width: float) -> List[str]:
        """Wrap text to fit within width."""
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

    def draw_title(self, text: str) -> None:
        """Draw the main title (service name and date)."""
        self._ensure_space(40)
        lines = self._wrap(text, self.fonts.title_name, self.fonts.title_size, BODY_WIDTH)
        for line in lines:
            self.canvas.setFont(self.fonts.title_name, self.fonts.title_size)
            self.canvas.drawString(MARGIN_X, PAGE_HEIGHT - self.cursor_y, line)
            self.cursor_y += self.fonts.title_size + 5

    def draw_item(
        self,
        title: str,
        description: Optional[str] = None,
        html_details: Optional[List[Dict[str, object]]] = None,
    ) -> None:
        """Draw a single service item with title, description, and details."""
        # Item title
        self._ensure_space(30)
        lines = self._wrap(title, self.fonts.heading_name, self.fonts.heading_size, BODY_WIDTH)
        for line in lines:
            self.canvas.setFont(self.fonts.heading_name, self.fonts.heading_size)
            self.canvas.drawString(MARGIN_X, PAGE_HEIGHT - self.cursor_y, line)
            self.cursor_y += self.fonts.heading_size + 3

        # Description (if present)
        if description and description.strip():
            self._ensure_space(20)
            desc_lines = self._wrap(
                description, self.fonts.body_name, self.fonts.body_size, BODY_WIDTH
            )
            self.canvas.setFont(self.fonts.body_name, self.fonts.body_size)
            for line in desc_lines:
                if self.cursor_y + self.fonts.body_size > PAGE_HEIGHT - MARGIN_Y:
                    self._new_page()
                self.canvas.drawString(MARGIN_X, PAGE_HEIGHT - self.cursor_y, line)
                self.cursor_y += self.fonts.body_size + 2
            self.cursor_y += 4  # Extra gap after description

        # HTML details
        if html_details:
            self._ensure_space(15)
            for para in html_details:
                text = para.get("text", "").strip()
                if not text:
                    continue
                is_bold = para.get("bold", False)
                font_name = self.fonts.heading_name if is_bold else self.fonts.body_name
                font_size = self.fonts.heading_size if is_bold else self.fonts.body_size

                lines = self._wrap(text, font_name, font_size, BODY_WIDTH - 20)
                self.canvas.setFont(font_name, font_size)
                for line in lines:
                    if self.cursor_y + font_size > PAGE_HEIGHT - MARGIN_Y:
                        self._new_page()
                    # Indent detail lines
                    self.canvas.drawString(MARGIN_X + 20, PAGE_HEIGHT - self.cursor_y, line)
                    self.cursor_y += font_size + 2

                # Line break type handling
                break_kind = para.get("break_kind", "p")
                if break_kind == "p":
                    self.cursor_y += 3  # Extra space after paragraph
                else:
                    self.cursor_y += 1  # Minimal space after br

        # Gap after item
        self.cursor_y += 8

    def add_attachment_pdf(self, attachment_bytes: bytes) -> None:
        """Add PDF attachment pages immediately after current item content."""
        # Finalize canvas before adding attachment (no separator page)
        self._finalize_canvas()
        
        # Add attachment as section
        try:
            reader = PdfReader(io.BytesIO(attachment_bytes))
            # Store as single section
            self.sections.append(('attachment', attachment_bytes))
        except Exception as e:
            print(f"  ⚠ Failed to process attachment PDF: {e}")

    def save(self, output_path: Path) -> None:
        """Save the PDF to disk, merging canvas and attachment sections in order."""
        # Finalize any remaining canvas content
        self._finalize_canvas()

        # Merge all sections in order
        writer = PdfWriter()

        for section_type, content in self.sections:
            try:
                reader = PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                print(f"  ⚠ Failed to process section: {e}")

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

        print(f"[OK] Saved leader guide to {output_path}")
