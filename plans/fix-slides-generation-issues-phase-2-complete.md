## Phase 2 Complete: Improve Lyrics PDF Filtering

Implemented comprehensive filtering of song part indicators from lyrics PDFs to prevent section labels from appearing on slides.

**Files created/changed:**
- packages/slides/slides_app/content_parser.py
- packages/slides/tests/test_lyrics_filtering.py (new)

**Functions created/changed:**
- `extract_lyrics_text()` - Enhanced with section indicator filtering logic

**Tests created/changed:**
- `test_strip_verse_chorus_indicators` - Verifies Verse/Chorus labels removed
- `test_strip_bridge_refrain_misc` - Verifies Bridge/Refrain/Misc removed
- `test_strip_indicators_with_punctuation` - Verifies punctuation variations handled
- `test_preserve_lyrics_after_indicator_on_same_line` - Verifies inline labels handled
- `test_strip_parenthetical_instructions` - Verifies (BRIDGE), (REPEAT 4X) removed
- `test_no_false_positives` - Verifies legitimate lyrics preserved
- `test_forever_reign_lyrics` - Integration test with real PDF patterns

**Review Status:** APPROVED

**Implementation Details:**
- Filters standalone section labels: Verse, Chorus, Bridge, Refrain, Intro, Outro, Ending, Interlude, Tag, Pre-Chorus, Instrumental, Misc
- Handles numeric variations: "Verse 1", "Chorus 2"
- Handles punctuation: "Verse 1:", "Chorus -", "Bridge (x2)"
- Strips parenthetical instructions: "(BRIDGE)", "(REPEAT 4X)"
- Intelligently preserves inline lyrics: "Verse 1: Amazing grace" → "Amazing grace"
- Avoids false positives by checking line length and word patterns

**Git Commit Message:**
```
feat: filter song part indicators from lyrics PDFs

- Remove standalone section labels (Verse, Chorus, Bridge, etc.)
- Handle numeric variations and punctuation (Verse 1:, Chorus -)
- Strip parenthetical instructions like (BRIDGE), (REPEAT 4X)
- Preserve inline lyrics when label and text share a line
- Add comprehensive test coverage for all indicator patterns
- Avoid false positives on legitimate lyrics containing these words
```
