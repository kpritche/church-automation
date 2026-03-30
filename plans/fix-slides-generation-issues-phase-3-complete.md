## Phase 3 Complete: Fix Red Text Filtering

Implemented reliable red text filtering with improved color detection and BeautifulSoup requirement.

**Files created/changed:**
- packages/slides/pyproject.toml - Added beautifulsoup4 dependency
- packages/slides/slides_app/content_parser.py - Enhanced _is_red_style() and _strip_highlight_and_red_text()
- packages/slides/tests/test_red_text_filtering.py (new)

**Functions created/changed:**
- `_is_red_style()` - Now uses RGB threshold detection (R>200, G<50, B<50) to catch red-ish colors
- `_strip_highlight_and_red_text()` - Required BeautifulSoup, removed regex fallback, loops until all red tags removed

**Tests created/changed:**
- `test_red_text_named_color` - Named "red" detection
- `test_red_text_hex_ff0000` - Hex color detection
- `test_red_text_hex_f00` - Short hex detection
- `test_red_text_rgb_255_0_0` - RGB format detection
- `test_red_text_single_quotes` - Single quote support
- `test_red_text_with_emphasis` - Nested tags
- `test_preserve_non_red_text` - No false positives
- `test_prayer_html_example` - Real-world example
- `test_red_ish_colors` - Red variants (#cc0000, #d0021b, etc.)

**Review Status:** APPROVED

**Implementation Details:**
- RGB threshold-based detection catches red-ish colors beyond pure #ff0000
- Handles hex (#f00, #ff0000, #cc0000), rgb(255,0,0), rgba, and named "red"
- Loops to handle nested tags properly (removes parent tags with red children)
- BeautifulSoup now required (added to dependencies)
- Removed unreliable regex fallback

**Git Commit Message:**
```
feat: improve red text filtering reliability

- Add beautifulsoup4 as required dependency
- Implement RGB threshold detection (R>200, G<50, B<50)
- Support hex, rgb, rgba, and named color formats
- Handle nested tags with iterative removal
- Remove unreliable regex fallback
- Add comprehensive test coverage for all color formats
```
