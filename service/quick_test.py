"""
Quick, dependency-light test harness for phrase parsing and slide slicing.

Usage:
  python service/quick_test.py                # uses built-in sample hymn text
  python service/quick_test.py path/to.txt    # reads raw text from a file

Outputs parsed phrases and the final slide texts to the console.
"""
import sys
from typing import List

from content_parser import _parse_html_details
from slide_utils import slice_into_slides


SAMPLE = (
    "How can we name a Love that wakens heart and mind, indwelling all we know or think or do or seek or find? "
    "Within our daily world, in every human face, Love's echoes sound and God is found, hid in the commonplace. "
    "If we awoke to life built on a rock of care that asked no great reward but firm, assured, was simply there, "
    "we can, with parents' names, describe, and thus adore, Love unconfined, a father kind, a mother strong and sure. "
    "When people share a task, and strength and skills unite in projects old or new, to make or do with shared delight, "
    "our Friend and Partner's will is better understood, that all should share, create, and care, and know that life is good. "
    "So in a hundred names, each day we all can meet a presence, sensed and shown at work, at home, or in the street. "
    "Yet every name we see, shines in a brighter sun: In Christ alone is Love full grown and life and hope begun."
)


def load_text_from_argv() -> str:
    if len(sys.argv) <= 1:
        return SAMPLE
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main() -> None:
    raw = load_text_from_argv()

    # Treat input as HTML-ish string; parser is robust to plain text
    parsed = _parse_html_details(raw)
    phrases: List[str] = [c["text"] for c in parsed]

    print("Parsed phrases ({}):".format(len(phrases)))
    for p in phrases:
        print("-", p)

    slides = slice_into_slides(phrases, max_chars=33, max_lines=2)
    print("\nSlides ({}):".format(len(slides)))
    for i, s in enumerate(slides, 1):
        print("--- Slide {} ---".format(i))
        print(s["text"])  # newline-separated lines


if __name__ == "__main__":
    main()

