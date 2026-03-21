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
COLUMN_GUTTER = 28
LEADER_COLUMN_WIDTH = 120
CONTENT_COLUMN_WIDTH = BODY_WIDTH - COLUMN_GUTTER - LEADER_COLUMN_WIDTH
CONTENT_COLUMN_X = MARGIN_X
LEADER_COLUMN_X = CONTENT_COLUMN_X + CONTENT_COLUMN_WIDTH + COLUMN_GUTTER
LEADER_RGB = (0.75, 0.1, 0.1)
SHADE_COLOR = (0.93, 0.95, 0.98)  # light blue-gray for alternating item rows

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
        bold_face = self._register("bold", "SourceSansPro-Bold", 14)
        regular_face = self._register("regular", "SourceSansPro-Regular", 12)

        self.title_name = bold_face
        self.heading_name = bold_face
        self.leader_name = bold_face
        self.column_label_name = bold_face
        self.body_name = regular_face
        self.small_name = regular_face

        self.title_size = 24
        self.heading_size = 14
        self.body_size = 12
        self.small_size = 10
        self.leader_size = 11
        self.column_label_size = 11

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
        self.column_headers_drawn = False
        self.item_index: int = 0  # increments per draw_item call; drives alternating shading

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

    def _line_height(self, line: Dict[str, object]) -> float:
        """Return total height consumed by a rendered line."""
        return float(line["size"]) + float(line["gap_after"])

    def _lines_height(self, lines: List[Dict[str, object]]) -> float:
        """Return total height for a list of rendered lines."""
        return sum(self._line_height(line) for line in lines)

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

    def _ensure_column_headers(self) -> None:
        """Draw the two column labels at the top of the first canvas page only."""
        if self.column_headers_drawn:
            return

        self.canvas.setFont(self.fonts.column_label_name, self.fonts.column_label_size)
        self.canvas.setFillColorRGB(0, 0, 0)
        label_y = PAGE_HEIGHT - self.cursor_y
        self.canvas.drawString(CONTENT_COLUMN_X, label_y, "Content")
        self.canvas.drawString(LEADER_COLUMN_X, label_y, "Leader(s)")
        self.cursor_y += self.fonts.column_label_size + 1

        divider_y = PAGE_HEIGHT - self.cursor_y
        self.canvas.line(MARGIN_X, divider_y, PAGE_WIDTH - MARGIN_X, divider_y)
        self.cursor_y += 14
        self.column_headers_drawn = True

    def _make_line_specs(
        self,
        text: str,
        font_name: str,
        size: float,
        width: float,
        *,
        indent: float = 0,
        color: Tuple[float, float, float] = (0, 0, 0),
        line_gap: float = 2,
        final_gap: Optional[float] = None,
    ) -> List[Dict[str, object]]:
        """Convert wrapped text into line specs for paginated rendering."""
        wrapped_lines = self._wrap(text, font_name, size, width)
        if not wrapped_lines:
            return []

        specs: List[Dict[str, object]] = []
        last_gap = line_gap if final_gap is None else final_gap
        for index, wrapped_line in enumerate(wrapped_lines):
            specs.append(
                {
                    "text": wrapped_line,
                    "font_name": font_name,
                    "size": size,
                    "indent": indent,
                    "color": color,
                    "gap_after": last_gap if index == len(wrapped_lines) - 1 else line_gap,
                }
            )
        return specs

    def _build_content_lines(
        self,
        title: str,
        description: Optional[str],
        html_details: Optional[List[Dict[str, object]]],
    ) -> List[Dict[str, object]]:
        """Build wrapped line specs for the main content column."""
        lines: List[Dict[str, object]] = []
        lines.extend(
            self._make_line_specs(
                title,
                self.fonts.heading_name,
                self.fonts.heading_size,
                CONTENT_COLUMN_WIDTH,
                final_gap=5,
            )
        )

        if description and description.strip():
            lines.extend(
                self._make_line_specs(
                    description.strip(),
                    self.fonts.body_name,
                    self.fonts.body_size,
                    CONTENT_COLUMN_WIDTH,
                    final_gap=6,
                )
            )

        if html_details:
            for para in html_details:
                text = str(para.get("text") or "").strip()
                if not text:
                    continue

                is_bold = bool(para.get("bold"))
                font_name = self.fonts.heading_name if is_bold else self.fonts.body_name
                font_size = self.fonts.heading_size if is_bold else self.fonts.body_size
                break_kind = str(para.get("break_kind") or "p")
                final_gap = 5 if break_kind == "p" else 2
                lines.extend(
                    self._make_line_specs(
                        text,
                        font_name,
                        font_size,
                        CONTENT_COLUMN_WIDTH - 20,
                        indent=20,
                        final_gap=final_gap,
                    )
                )

        return lines

    def _build_leader_lines(self, leaders: Optional[List[str]]) -> List[Dict[str, object]]:
        """Build wrapped line specs for the leader column."""
        leader_lines: List[Dict[str, object]] = []
        for leader in leaders or []:
            clean_leader = leader.strip()
            if not clean_leader:
                continue
            leader_lines.extend(
                self._make_line_specs(
                    clean_leader,
                    self.fonts.leader_name,
                    self.fonts.leader_size,
                    LEADER_COLUMN_WIDTH,
                    color=LEADER_RGB,
                    final_gap=4,
                )
            )
        return leader_lines

    def _consume_page_lines(
        self,
        lines: List[Dict[str, object]],
        available_height: float,
    ) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
        """Split line specs into what fits on the current page and what remains."""
        if not lines:
            return [], []

        used_height = 0.0
        fitting_count = 0
        for line in lines:
            line_height = self._line_height(line)
            if fitting_count > 0 and used_height + line_height > available_height:
                break
            if fitting_count == 0 and line_height > available_height:
                fitting_count = 1
                used_height = line_height
                break
            if used_height + line_height > available_height:
                break
            used_height += line_height
            fitting_count += 1

        return lines[:fitting_count], lines[fitting_count:]

    def _draw_line_block(self, lines: List[Dict[str, object]], column_x: float, start_y: float) -> float:
        """Draw line specs into a column and return the rendered block height."""
        rendered_height = 0.0
        for line in lines:
            self.canvas.setFont(str(line["font_name"]), float(line["size"]))
            color = line["color"]
            self.canvas.setFillColorRGB(*color)
            draw_y = PAGE_HEIGHT - start_y - rendered_height
            self.canvas.drawString(column_x + float(line["indent"]), draw_y, str(line["text"]))
            rendered_height += self._line_height(line)

        self.canvas.setFillColorRGB(0, 0, 0)
        return rendered_height

    def draw_title(self, text: str) -> None:
        """Draw the main title (service name and date)."""
        self._ensure_space(40)
        lines = self._wrap(text, self.fonts.title_name, self.fonts.title_size, CONTENT_COLUMN_WIDTH)
        for line in lines:
            self.canvas.setFont(self.fonts.title_name, self.fonts.title_size)
            self.canvas.drawString(CONTENT_COLUMN_X, PAGE_HEIGHT - self.cursor_y, line)
            self.cursor_y += self.fonts.title_size + 5

    def draw_item(
        self,
        title: str,
        description: Optional[str] = None,
        html_details: Optional[List[Dict[str, object]]] = None,
        leaders: Optional[List[str]] = None,
    ) -> None:
        """Draw a single service item with content on the left and leaders on the right."""
        self.item_index += 1
        shade = (self.item_index % 2 == 0)

        content_lines = self._build_content_lines(title, description, html_details)
        leader_lines = self._build_leader_lines(leaders)

        while content_lines or leader_lines:
            self._ensure_column_headers()
            available_height = PAGE_HEIGHT - MARGIN_Y - self.cursor_y
            if available_height <= 0:
                self._new_page()
                continue

            content_page, remaining_content = self._consume_page_lines(content_lines, available_height)
            leader_page, remaining_leaders = self._consume_page_lines(leader_lines, available_height)

            if not content_page and not leader_page:
                self._new_page()
                continue

            block_top = self.cursor_y
            block_height = max(
                self._lines_height(content_page),
                self._lines_height(leader_page),
            )

            if shade:
                # cap: extend rect above the first-line baseline to cover ascenders of title
                # trim: leave a few points of space before the next item at the bottom
                cap = self.fonts.heading_size - 2
                trim = 4
                rect_y = PAGE_HEIGHT - block_top - block_height + trim
                self.canvas.setFillColorRGB(*SHADE_COLOR)
                self.canvas.rect(
                    MARGIN_X - 4,
                    rect_y,
                    BODY_WIDTH + 8,
                    block_height + cap - trim,
                    fill=1,
                    stroke=0,
                )

            content_height = self._draw_line_block(content_page, CONTENT_COLUMN_X, block_top)
            leader_height = self._draw_line_block(leader_page, LEADER_COLUMN_X, block_top)
            self.cursor_y = block_top + max(content_height, leader_height)

            content_lines = remaining_content
            leader_lines = remaining_leaders
            if content_lines or leader_lines:
                self._new_page()

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
