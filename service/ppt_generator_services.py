# ppt_generator_services.py
"""
Generate a PowerPoint (.pptx) where each slide is black background with white, centered, larger text,
with special handling for call-and-response slides.
Slides are provided as a list of dicts:
  { text: str, style: 'blank' or 'content' }

- 16:9 ratio at 1920x1080 pixels (96 DPI)
- Calls ("Leader:"/"L:") are white text
- Responses ("People:"/"P:") start on their own slides with goldenrod text
- If a slide's two lines contain a call and a response, they are split into two slides

Usage:
    from ppt_generator_services import create_pptx_for_items
    create_pptx_for_items(slides, "service_slides.pptx")

Prerequisites:
    pip install python-pptx
"""
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_VERTICAL_ANCHOR
from typing import List, Dict

CALL_MARKERS = ("Leader:", "L:")
RESPONSE_MARKERS = ("People:", "P:")
GOLDENROD = RGBColor(218, 165, 32)
WHITE = RGBColor(255, 255, 255)


def create_pptx_for_items(
    slides: List[Dict[str, str]],
    filename: str = "service_slides.pptx"
) -> None:
    """
    Create a .pptx file where each slide in `slides` is added in order.

    slides: list of { 'text': str, 'style': 'blank'|'content' }
    filename: output file path
    """
    # Initialize presentation with custom slide size
    prs = Presentation()
    # Set slide dimensions for 1920x1080 px at 96 DPI
    emu_per_px = int(914400 / 96)
    prs.slide_width = Emu(1920 * emu_per_px)
    prs.slide_height = Emu(1080 * emu_per_px)

    blank_layout = prs.slide_layouts[6]

    def add_text_slide(text: str, color: RGBColor) -> None:
        sl = prs.slides.add_slide(blank_layout)
        # Black background
        bg = sl.background
        bg.fill.solid()
        bg.fill.fore_color.rgb = RGBColor(0, 0, 0)
        # Full-slide textbox
        txbox = sl.shapes.add_textbox(0, 0, prs.slide_width, prs.slide_height)
        tf = txbox.text_frame
        tf.clear()
        tf.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.size = Pt(80)
        run.font.name = 'Arial'
        run.font.color.rgb = color
        p.alignment = PP_ALIGN.CENTER

    for slide in slides:
        text = slide.get('text', '').strip()
        # Blank slide
        if slide.get('style') == 'blank' or not text:
            prs.slides.add_slide(blank_layout)
            continue

        lines = text.split('\n')
        # Case: slide contains exactly two lines, one call and one response
        if len(lines) == 2 and lines[0].startswith(CALL_MARKERS) and lines[1].startswith(RESPONSE_MARKERS):
            add_text_slide(lines[0], WHITE)
            add_text_slide(lines[1], GOLDENROD)
            continue

        # General: process each line or group
        # If first line is a call marker
        if lines[0].startswith(CALL_MARKERS):
            # Combine up to two lines of call
            call_text = lines[0] + (f"\n{lines[1]}" if len(lines) > 1 and not lines[1].startswith(RESPONSE_MARKERS) else "")
            add_text_slide(call_text, WHITE)
            # If second line is response, handle separately
            if len(lines) > 1 and lines[1].startswith(RESPONSE_MARKERS):
                add_text_slide(lines[1], GOLDENROD)
            continue

        # If first line is a response
        if lines[0].startswith(RESPONSE_MARKERS):
            resp_text = lines[0] + (f"\n{lines[1]}" if len(lines) > 1 else "")
            add_text_slide(resp_text, GOLDENROD)
            continue

        # Default: normal content slide (white text)
        # Combine up to two lines
        combined = lines[0] + (f"\n{lines[1]}" if len(lines) > 1 else "")
        add_text_slide(combined, WHITE)

    prs.save(filename)
