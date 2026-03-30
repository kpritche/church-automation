## Plan: Fix ProPresenter Slides Generation Issues

Fix song handling for SongSelect songs, improve lyrics PDF filtering of song part indicators, ensure reliable red text removal from PCO content, eliminate extra commas after punctuation, and add BitFocus Companion camera control via ProPresenter communication actions.

**Phases: 6**

---

### **Phase 1: Add Song Skip Configuration**
- **Objective:** Skip song slide generation for SongSelect songs (detected by "songselect" in attachment filenames) and provide manual exclusion options
- **Files/Functions to Modify/Create:**
  - `packages/slides/slides_config.json` - Add `song_handling` configuration section
  - `packages/slides/slides_app/make_pro.py` - Add skip logic before song slide generation (around line 377-450)
- **Tests to Write:**
  - `test_song_skip_by_songselect_attachment` - Verify songs with "songselect" in any attachment filename are skipped
  - `test_song_skip_by_title` - Verify exact title matching from config skips generation
  - `test_song_skip_by_regex` - Verify regex pattern matching works
  - `test_song_skip_case_insensitive` - Verify "SongSelect", "songselect", "SONGSELECT" all match
  - `test_song_not_skipped_without_songselect` - Verify songs without SongSelect attachments still generate
- **Steps:**
  1. Write test for SongSelect attachment detection that expects song to be skipped
  2. Extend `slides_config.json` with `song_handling` section:
     ```json
     "song_handling": {
       "skip_songselect_songs": true,
       "skip_exact_titles": [],
       "skip_title_patterns": [],
       "always_generate_titles": []
     }
     ```
  3. In `make_pro.py`, load config and implement `should_skip_song()` function that:
     - Checks if `skip_songselect_songs` is enabled
     - If yes, calls `fetch_lyrics_attachments()` and checks if any filename contains "songselect" (case-insensitive)
     - Also checks exact title and regex pattern skip lists from config
     - Returns True if song should be skipped
  4. Add skip check immediately after `extract_items_from_pypco()` call, before song processing
  5. Add logging: `print(f"⊘ Skipping song '{parsed['title']}' (SongSelect detected in attachments)")` 
  6. Run tests to verify SongSelect songs are skipped and others are processed

---

### **Phase 2: Improve Lyrics PDF Filtering**
- **Objective:** Strip song part indicators (Verse 1, Chorus, Bridge, Refrain, Misc, etc.) from lyrics PDFs
- **Files/Functions to Modify/Create:**
  - `packages/slides/slides_app/content_parser.py` - Enhance `extract_lyrics_text()` function (around lines 625-700)
- **Tests to Write:**
  - `test_strip_verse_chorus_indicators` - Verify "Verse 1", "Verse 2", "Chorus 1" removed
  - `test_strip_bridge_refrain_misc` - Verify "Bridge", "Refrain", "Misc 1" removed
  - `test_strip_indicators_with_punctuation` - Verify "Verse 1:", "Chorus -", "Bridge (x2)" handled
  - `test_preserve_lyrics_after_indicator_on_same_line` - Verify "Verse 1: Amazing grace" keeps "Amazing grace"
  - `test_strip_parenthetical_instructions` - Verify "(BRIDGE)", "(REPEAT 4X)" removed
  - `test_no_false_positives` - Verify legitimate lyrics containing "verse", "chorus" aren't removed
- **Steps:**
  1. Write tests with sample lyrics containing various song part indicators
  2. In `extract_lyrics_text()`, add dedicated section indicator filtering after existing filters
  3. Create comprehensive regex pattern for standalone section labels:
     ```python
     # Match lines that are ONLY section indicators (with optional punctuation)
     section_pattern = r'^\s*(Verse|Chorus|Bridge|Refrain|Intro|Outro|Ending|Interlude|Tag|Pre-Chorus|Instrumental|Misc)\s*\d*\s*[:\-\.]?\s*$'
     ```
  4. Create pattern for parenthetical instructions: `r'^\s*\([^)]*\)\s*$'` (matches "(BRIDGE)", "(REPEAT 4X)")
  5. Handle inline labels by detecting `^(Section Label)\d*:\s*(.+)` and keeping only the `.+` part
  6. Filter lines case-insensitively
  7. Run tests against Forever Reign lyrics to verify "Verse 1", "Verse 2", "Chorus 1", "Verse 3", "Misc 1", "(BRIDGE)", "(REPEAT 4X)" are all removed

---

### **Phase 3: Fix Red Text Filtering Reliability**
- **Objective:** Ensure red text is consistently removed from PCO content regardless of color format
- **Files/Functions to Modify/Create:**
  - `packages/slides/pyproject.toml` - Add `beautifulsoup4` as explicit dependency
  - `packages/slides/slides_app/content_parser.py` - Enhance `_is_red_style()` and `_strip_highlight_and_red_text()` (around lines 81-165)
- **Tests to Write:**
  - `test_red_text_hex_ff0000` - Verify `color: #ff0000` removal
  - `test_red_text_rgb_255_0_0` - Verify `color: rgb(255,0,0)` removal  
  - `test_red_text_named_red` - Verify `color: red` removal
  - `test_red_text_single_quotes` - Verify `style='color: red'` removal
  - `test_red_text_with_emphasis` - Verify red text with `<em>` tags removed together
  - `test_preserve_non_red_text` - Verify black/other colored text preserved
- **Steps:**
  1. Write tests using prayer.html as reference (contains `<span style="color: #ff0000;"><em>Leader: </em>...</span>`)
  2. Add `beautifulsoup4` to `packages/slides/pyproject.toml` dependencies (no version constraint)
  3. Update `_is_red_style()` to properly parse CSS `color:` property and detect RGB values where R > 200 and G,B < 50
  4. Support hex formats: `#f00`, `#ff0000`, `#cc0000`, and similar red-ish colors
  5. Support rgb(): any `rgb(R, G, B)` where R > 200 and G,B < 50
  6. Remove the regex fallback path entirely (require BeautifulSoup, which will now always be installed)
  7. Run tests with prayer.html to verify all red text (including "Leader:" instructions) is removed

---

### **Phase 4: Fix Extra Comma After Punctuation**
- **Objective:** Stop inserting commas after terminal punctuation when merging short text chunks
- **Files/Functions to Modify/Create:**
  - `packages/slides/slides_app/content_parser.py` - Fix merge logic in `_parse_html_details()` (around lines 311-323)
- **Tests to Write:**
  - `test_no_comma_after_period` - Verify "Hello." + "Amen" → "Hello. Amen" not "Hello., Amen"
  - `test_no_comma_after_exclamation` - Verify "So." + "Amen" → "So. Amen" not "So., Amen"
  - `test_no_comma_after_question` - Verify punctuation ? handling
  - `test_comma_when_no_punctuation` - Verify comma still added when appropriate
  - `test_benediction_specific` - Use benediction text to verify "AMEN." + "BUEN CAMINO" → no extra comma
- **Steps:**
  1. Write tests including specific benediction case ("MAY IT BE SO. AMEN." should not produce "AMEN., ")
  2. Locate the chunk merge logic in `_parse_html_details()` where it does: `merged[-1]["text"] + ", " + chunk["text"]`
  3. Add check before merging: if previous chunk ends with terminal punctuation (`.?!;:`) or already ends with comma, use space-only joiner
  4. Implementation:
     ```python
     prev_text = merged[-1]["text"]
     if prev_text.rstrip().endswith(('.', '?', '!', ';', ':', ',')):
         merged[-1]["text"] = (prev_text + " " + chunk["text"]).strip()
     else:
         merged[-1]["text"] = (prev_text + ", " + chunk["text"]).strip(', ')
     ```
  5. Run tests to verify no more ".,", "!,", "?,", ";," artifacts

---

### **Phase 5: Add Communication Action Configuration**
- **Objective:** Create configuration structure for BitFocus Companion camera control via ProPresenter communication actions
- **Files/Functions to Modify/Create:**
  - `packages/slides/slides_config.json` - Add `camera_control` configuration section
  - `packages/slides/slides_app/communication_actions.py` - NEW: Create utility module for communication actions
- **Tests to Write:**
  - `test_load_camera_control_config` - Verify config loading
  - `test_create_communication_action_protobuf` - Verify Action protobuf structure
  - `test_match_countdown` - Verify "Countdown" → "CC 9/1/0"
  - `test_match_welcome` - Verify "Welcome" → "CC 9/2/0"
  - `test_match_prayer` - Verify "Prayer" → "CC 9/3/0"
  - `test_match_first_up_song` - Verify "First Up Song" → "CC 9/4/0"
  - `test_match_scripture_reading` - Verify "Scripture Reading" → "CC 9/2/1"
  - `test_no_match_returns_none` - Verify unmapped items return None
- **Steps:**
  1. Write tests for config loading and title matching
  2. Add `camera_control` section to `slides_config.json`:
     ```json
     "camera_control": {
       "enabled": true,
       "device": {
         "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
         "name": "Companion"
       },
       "command": {
         "format": "CC x",
         "replacement_range": {"start": 3, "end": 4}
       },
       "mappings": [
         {"title": "Countdown", "command": "CC 9/1/0"},
         {"title": "Welcome", "command": "CC 9/2/0"},
         {"title": "Prayer", "command": "CC 9/3/0"},
         {"title": "First Up Song", "command": "CC 9/4/0"},
         {"title": "Celebrate Song", "command": "CC 9/5/0"},
         {"title": "Passing Peace", "command": "CC 9/6/0"},
         {"title": "Children's Moment", "command": "CC 9/7/0"},
         {"title": "The Message", "command": "CC 9/1/1"},
         {"title": "Scripture Reading", "command": "CC 9/2/1"},
         {"title": "MiM Bells", "command": "CC 9/3/1"},
         {"title": "MiM Piano", "command": "CC 9/4/1"},
         {"title": "MiM Choir+Keys", "command": "CC 9/5/1"},
         {"title": "MiM Choir", "command": "CC 9/6/1"},
         {"title": "Benediction", "command": "CC 9/7/1"}
       ]
     }
     ```
  3. Create `packages/slides/slides_app/communication_actions.py` with:
     - `load_camera_control_config()` - Load and parse config
     - `get_camera_command_for_item(title, config)` - Match title to command (exact match, case-insensitive)
     - `create_communication_action(command, config)` - Create protobuf Action with ACTION_TYPE_COMMUNICATION
  4. Import protobuf modules: `action_pb2`, `uuid_pb2`, `int_range_pb2`, `collection_element_type_pb2`
  5. Implement `create_communication_action()`:
     - Create Action with random UUID
     - Set `action.type = ACTION_TYPE_COMMUNICATION`
     - Set `action.isEnabled = True`
     - Set `action.name = "Custom Control"`
     - Set `action.communication.deviceIdentification.parameterUuid.string` = device UUID from config
     - Set `action.communication.deviceIdentification.parameterName` = device name from config
     - Set `action.communication.format` = format from config
     - Set `action.communication.description` = "Executes camera control command."
     - Add command to `action.communication.commands[]` with replacement range
  6. Run tests to verify config loading and command matching work correctly

---

### **Phase 6: Insert Communication Actions into Presentations**
- **Objective:** Automatically add camera control communication action as first action in the first cue of each presentation
- **Files/Functions to Modify/Create:**
  - `packages/slides/slides_app/make_pro.py` - Add communication action insertion (around line 274-276 where cues are added)
- **Tests to Write:**
  - `test_communication_action_added_to_first_cue` - Verify action is in first cue's actions list
  - `test_communication_action_has_correct_command` - Verify command matches configured mapping
  - `test_communication_action_device_matches_config` - Verify device UUID/name are correct
  - `test_no_action_when_no_mapping` - Verify presentations without mapping don't get action
  - `test_presentation_valid_after_insertion` - Verify `.pro` file loads in ProPresenter
- **Steps:**
  1. Write tests for communication action insertion
  2. Import `communication_actions` module in `make_pro.py`
  3. Load camera control config after loading slides config
  4. In the slide generation loop (around line 360-450), after getting `parsed` from `extract_items_from_pypco()`:
     - Call `get_camera_command_for_item(parsed['title'], camera_config)`
     - If command is found, create communication action via `create_communication_action(command, camera_config)`
  5. When creating/copying the first cue for this presentation:
     - Insert the communication action as the FIRST action in `cue.actions` (before the slide action)
     - This ensures camera switches before slide displays
  6. Add logging: `print(f"✓ Added camera control: {command} for '{parsed['title']}'")` 
  7. Test manually by:
     - Generating slides with `make-slides`
     - Loading generated `.pro` files in ProPresenter
     - Verifying communication actions appear and trigger correctly
  8. Run tests to verify insertion and structure validity

---

## Implementation Notes

### SongSelect Detection (Phase 1)
- Check ALL attachments for a given PCO item, not just the first one
- Case-insensitive search: `"songselect" in filename.lower()`
- Lead sheets, chord charts, and lyrics from SongSelect all contain "songselect" in filename

### Song Part Indicator Patterns (Phase 2)
From Forever Reign lyrics.pdf, observed patterns:
- `Verse 1`, `Verse 2`, `Verse 3` (standalone lines)
- `Chorus 1` (standalone line)
- `Misc 1` (standalone line)
- `(BRIDGE)` (parenthetical on own line)
- `(REPEAT 4X)` (parenthetical on own line)

Pattern should match case-insensitively and handle variations with/without numbers, colons, dashes, parentheses.

### Red Text Detection (Phase 3)
From prayer.html, observed patterns:
- `<span style="color: #ff0000;">...</span>`
- `<span style="color: #ff0000;"><em>Leader: </em>...</span>` (nested tags)
- Red text includes instructional content ("Leader:", "Hear this:") that should be removed

### Punctuation Error (Phase 4)
From benediction.pro screenshot:
- Current output: `"AMEN., "BUEN CAMINO!""`
- Expected output: `"AMEN. "BUEN CAMINO!""`
- Root cause: merge logic always adds `", "` even after terminal punctuation

### Communication Action Structure (Phase 5-6)
From "Greeting Each Other.pro", exact structure required:
- Device UUID: `DA2125C2-2809-4822-85BE-A614022530BC`
- Device Name: `Companion`
- Action name: `Custom Control`
- Format: `CC x` (where `x` is placeholder at index 3)
- Replacement range: start=3, end=4
- Command value examples: `CC 9/6/0`, `CC 9/1/0`, etc.

### Testing Strategy
Each phase follows TDD:
1. Write failing tests first
2. Implement minimal code to pass tests
3. Verify tests pass
4. Run full test suite to ensure no regressions
5. Manual verification with real ProPresenter whenever appropriate

---

## Configuration Files Required

### slides_config.json (after all phases)
```json
{
  "song_handling": {
    "skip_songselect_songs": true,
    "skip_exact_titles": [],
    "skip_title_patterns": [],
    "always_generate_titles": []
  },
  "camera_control": {
    "enabled": true,
    "device": {
      "uuid": "DA2125C2-2809-4822-85BE-A614022530BC",
      "name": "Companion"
    },
    "command": {
      "format": "CC x",
      "replacement_range": {"start": 3, "end": 4}
    },
    "mappings": [
      {"title": "Countdown", "command": "CC 9/1/0"},
      {"title": "Welcome", "command": "CC 9/2/0"},
      {"title": "Prayer", "command": "CC 9/3/0"},
      {"title": "First Up Song", "command": "CC 9/4/0"},
      {"title": "Celebrate Song", "command": "CC 9/5/0"},
      {"title": "Passing Peace", "command": "CC 9/6/0"},
      {"title": "Children's Moment", "command": "CC 9/7/0"},
      {"title": "The Message", "command": "CC 9/1/1"},
      {"title": "Scripture Reading", "command": "CC 9/2/1"},
      {"title": "MiM Bells", "command": "CC 9/3/1"},
      {"title": "MiM Piano", "command": "CC 9/4/1"},
      {"title": "MiM Choir+Keys", "command": "CC 9/5/1"},
      {"title": "MiM Choir", "command": "CC 9/6/1"},
      {"title": "Benediction", "command": "CC 9/7/1"}
    ]
  }
}
```

---

## Decisions Made

1. **Song skip edge cases**: ✅ Skip ANY song with SongSelect attachments, even if it has local `.pro` files
2. **Camera control for unmapped items**: ✅ Log a warning when item has no camera mapping
3. **Communication action position**: ✅ First action in first cue (before slide action)
4. **Testing with real ProPresenter**: ✅ User has ProPresenter 7.21+ for validation
5. **Multiple title variations**: ✅ Support multiple PCO title variations mapping to same camera command (e.g., "Prayer", "Prayers", "Prayer of Confession" all map to CC 9/3/0)
