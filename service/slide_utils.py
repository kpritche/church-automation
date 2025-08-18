# slide_utils.py
"""
Functions to slice text_chunks into slides abiding by:
- no more than two lines per slide
- no more than 35 characters per line
Each slide dict has:
  - text: a string with 1-2 lines separated by newline
  - style: 'content' (for PPT generator)
"""
from typing import List, Dict


def _split_long_word(word: str, max_chars: int) -> List[str]:
    """
    Break a single word into multiple chunks of at most max_chars.
    """
    return [word[i:i+max_chars] for i in range(0, len(word), max_chars)]


def slice_into_slides(
    text_chunks: List[str],
    max_chars: int = 33,
    max_lines: int = 2
) -> List[Dict[str, str]]:
    """
    Convert a list of paragraphs (text_chunks) into a list of slides,
    each obeying the constraints:
      - <= max_lines lines per slide
      - <= max_chars characters per line

    Returns:
        List of dicts with keys:
          - 'text': slide text (lines joined by '\n')
          - 'style': 'content'
    """
    slides: List[Dict[str, str]] = []

    for chunk in text_chunks:
        # Split into words and handle any overly long words
        words = chunk.strip().split()
        tokens: List[str] = []
        for w in words:
            if len(w) > max_chars:
                tokens.extend(_split_long_word(w, max_chars))
            else:
                tokens.append(w)

        # Build lines by greedily filling up to max_chars
        lines: List[str] = []
        current_line = ""
        for token in tokens:
            if not current_line:
                current_line = token
            elif len(current_line) + 1 + len(token) <= max_chars:
                current_line += " " + token
            else:
                lines.append(current_line)
                current_line = token
        # append any remaining text
        if current_line:
            lines.append(current_line)

        # Group lines into slides of up to max_lines
        for i in range(0, len(lines), max_lines):
            slide_lines = lines[i:i + max_lines]
            slide_text = "\n ".join(slide_lines)
            slides.append({"text": slide_text, "style": "content"})

    return slides
