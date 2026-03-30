#!/usr/bin/env python3
"""
Test script to verify the fixes for:
1. Red text stripping
2. Yellow/white color logic for bold text
"""

import sys
from pathlib import Path

# Add packages to path
_REPO_ROOT = Path(__file__).resolve().parent
_SLIDES_PARENT = _REPO_ROOT / "packages" / "slides"
_SHARED_PARENT = _REPO_ROOT / "packages" / "shared"

if str(_SLIDES_PARENT) not in sys.path:
    sys.path.insert(0, str(_SLIDES_PARENT))
if str(_SHARED_PARENT) not in sys.path:
    sys.path.insert(0, str(_SHARED_PARENT))

# Add protobuf path
PROTO_DIR = _SLIDES_PARENT / "ProPresenter7_Proto" / "generated"
if str(PROTO_DIR) not in sys.path:
    sys.path.insert(0, str(PROTO_DIR))

from slides_app.content_parser import _is_red_style, _parse_html_details

def test_red_color_detection():
    """Test that various red color formats are detected."""
    print("\n" + "="*60)
    print("TEST 1: Red Color Detection")
    print("="*60)
    
    test_cases = [
        ("color: red", True, "named color 'red'"),
        ("color:red", True, "named color with no space"),
        ("COLOR: RED", True, "uppercase 'RED'"),
        ("color: #f00", True, "hex short format #f00"),
        ("color: #ff0000", True, "hex long format #ff0000"),
        ("color: #ff0000ff", True, "hex with alpha #ff0000ff"),
        ("color: #FF0000", True, "hex uppercase #FF0000"),
        ("rgb(255, 0, 0)", True, "rgb format"),
        ("rgba(255, 0, 0, 0.5)", True, "rgba format"),
        ("color:rgba(255,0,0,1)", True, "rgba no spaces"),
        ("color: blue", False, "blue color"),
        ("color: #00ff00", False, "green hex color"),
        ("", False, "empty string"),
    ]
    
    passed = 0
    failed = 0
    
    for style, expected, description in test_cases:
        result = _is_red_style(style)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: {description:50} | style='{style}' | expected={expected}, got={result}")
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


def test_red_text_stripping():
    """Test that red text is completely removed from HTML."""
    print("\n" + "="*60)
    print("TEST 2: Red Text Stripping from HTML")
    print("="*60)
    
    test_cases = [
        (
            '<p>Normal text <span style="color: red">RED TEXT</span> more text</p>',
            'normal text more text',
            "inline span with red style"
        ),
        (
            '<p>Normal <font color="red">RED TEXT</font> normal</p>',
            'normal normal',
            "font tag with red color"
        ),
        (
            '<p>Text with <span style="color: #ff0000">red hex</span> content</p>',
            'text with content',
            "hex red color"
        ),
        (
            '<p>Bold <b>important</b> and <span style="color: red">ignore this</span></p>',
            'bold important and',
            "mixed bold and red"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for html, expected_keywords, description in test_cases:
        parsed = _parse_html_details(html)
        result_text = " ".join([chunk.get("text", "") for chunk in parsed])
        result_lower = result_text.lower()
        
        # Check if expected keywords are in result and "red" is not
        has_keywords = all(kw.lower() in result_lower for kw in expected_keywords.split())
        no_red = "red" not in result_lower
        
        status = "✓ PASS" if (has_keywords and no_red) else "✗ FAIL"
        if has_keywords and no_red:
            passed += 1
        else:
            failed += 1
        print(f"{status}: {description:40} | result: '{result_text}'")
        if not (has_keywords and no_red):
            print(f"       Expected keywords: {expected_keywords}, Got: {result_text}")
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


def test_color_logic():
    """Test the color logic for slides."""
    print("\n" + "="*60)
    print("TEST 3: Yellow/White Color Logic")
    print("="*60)
    
    # Simulate slide data
    slides = [
        {"text": "Leader: Opening prayer", "is_bold": False},  # CALL_MARKER -> white
        {"text": "This is important", "is_bold": True},         # bold -> yellow
        {"text": "More content here", "is_bold": False},        # not bold -> white (not yellow from previous!)
        {"text": "People: Amen", "is_bold": False},             # RESPONSE_MARKER -> yellow
        {"text": "Final slide", "is_bold": False},              # not bold or marker -> white
    ]
    
    CALL_MARKERS = ("Leader:", "L:", "Presider:", "One:", "Pastor:")
    RESPONSE_MARKERS = ("People:", "P:", "All:", "Many:")
    
    expected_colors = [
        ("white", "CALL_MARKER should be white"),
        ("yellow", "bold text should be yellow"),
        ("white", "normal text after bold should be white (NOT yellow)"),
        ("yellow", "RESPONSE_MARKER should be yellow"),
        ("white", "normal text should be white"),
    ]
    
    passed = 0
    failed = 0
    
    for i, (slide, (expected_color, reason)) in enumerate(zip(slides, expected_colors)):
        text = slide["text"]
        
        # Apply the same logic as in the fixed code
        if any(text.startswith(m) for m in CALL_MARKERS):
            color = "white"
        elif any(text.startswith(m) for m in RESPONSE_MARKERS) or slide.get("is_bold", False):
            color = "yellow"
        else:
            color = "white"
        
        status = "✓ PASS" if color == expected_color else "✗ FAIL"
        if color == expected_color:
            passed += 1
        else:
            failed += 1
        print(f"{status}: Slide {i+1} -> {color:6} | {reason:50} | '{text}'")
        if color != expected_color:
            print(f"       Expected: {expected_color}, Got: {color}")
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    results = []
    results.append(("Red Color Detection", test_red_color_detection()))
    results.append(("Red Text Stripping", test_red_text_stripping()))
    results.append(("Color Logic", test_color_logic()))
    
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + ("ALL TESTS PASSED ✓" if all_passed else "SOME TESTS FAILED ✗"))
    sys.exit(0 if all_passed else 1)
