# ProPresenter Automation Implementation Plan

This document provides detailed instructions for an AI agent to refactor and extend the `church-automation` slides package. The goal is to move from a string-replacement approach to a robust Protobuf-based "Message-Injection" system for generating ProPresenter 7.21.2 files and uploading them to Planning Center Online (PCO).

## 🎯 Project Goals
1. **Protobuf Generation:** Generate functional `.pro` files using the 7.21.2 schema.
2. **Bundle Support:** Generate `.probundle` files for announcement slides containing media.
3. **PCO Integration:** Automatically upload generated files to specific PCO Service Items.
4. **Typography & Styling:** Enforce strict branding (Source Sans Pro, Uppercase, specific palette).
5. **Device Control:** Trigger external hardware via RossTalk custom commands injected into the first slide.

## 🛠 Technical Requirements
- **Target Version:** Strictly ProPresenter 7.21.2 (schemas in `packages/slides/ProPresenter7_Proto/proto7.21.2/`).
- **Generation Strategy:** Hybrid approach—load minimal templates, clear existing `cues`, and inject new `Cue` messages by cloning prototypes.
- **Action Mapping:** Use a provided mapping (Service Item type -> RossTalk command) to determine which action to attach.
- **PCO API:** Use `pypco` for Service Item attachments.
- **RTF Generation:** Binary RTF blobs in `rtf_data` must be uppercase and single-style per slide.

## 📏 Styling Constraints
- **Font:** Mandatory "Source Sans Pro" family.
- **Case:** All text MUST be converted to `UPPERCASE`.
- **Palette:** #000000, #16463e, #51bf9b, #ff7f30, #6fcfeb, #cda787, #ffffff.
- **Templates:**
  - `white_template_mac.pro`: For Leader/Call lines (typically White text).
  - `yellow_template_mac.pro`: For All/Response/Bold lines (typically Yellow text).
  - `song_template.pro`: For initializing a song presentation.
  - `prayer_template.pro`: For initializing a prayer presentation.
  - `blank_template_mac.pro`: A blank slide.
  - `rosstalk_template.pro`: A slide with a Rosstalk action.

---

## 🚀 Implementation Phases

### Phase 1: Protobuf Binding Generation
1. Locate schemas: `packages/slides/ProPresenter7_Proto/proto7.21.2/`.
2. Generate Python bindings using `protoc` into `packages/slides/ProPresenter7_Proto/generated_7_21_2/`.
3. Create `__init__.py` files to ensure the generated code is importable.

### Phase 2: RTF & Template Logic
1. **RTF Utility:** In `packages/slides/slides_app/slide_utils.py`, implement a function to generate binary RTF blobs.
   - Force `UPPERCASE`.
   - Set font to "Source Sans Pro" (Bold for yellow template, Regular/Semibold for white).
   - Apply a single per slide according to the template determined by information parsed from Planning Center.
2. **Message Injection:** Refactor `make_pro.py` to:
   - Load a template `.pro` file using the generated bindings.
   - Clear the `cues` list in the `Presentation` message.
   - For each text chunk:
     - Detect "Leader" vs "All" lines (e.g., `L:`, `P:`, `One:`, `Many:`).
     - Load/Clone a prototype `Cue` from the corresponding template file.
     - Replace the `rtf_data` in the cloned element with the new RTF blob.
     - Append the cloned `Cue` to the active `Presentation`.
3. **Action Injection:** 
   - On the first slide (`Cue`) of most presentations, inject a custom RossTalk Action.
   - Use a provided formatting example from the templates to understand the Protobuf structure for RossTalk actions.
   - Implement a mapping-based logic to select the correct RossTalk command based on the Service Item's context.

### Phase 3: Announcement ProBundles
1. **BundlePackager:** Create a utility to package `.pro` files and media.
2. **Archive Format:** Create a ZIP-based archive renamed to `.probundle`.
3. **Media Linking:** Ensure internal paths within the `.pro` file correctly reference media assets relative to the bundle root (reference `packages/announcements/announcements_app/pro_generator.py` for logic).

### Phase 4: PCO Integration
1. **Uploader Module:** Extend `make_pro.py` to support PCO uploads via `pypco`.
2. **Targeting:**
   - Resolve `Service Type` and `Plan`.
   - Find the specific `Service Item` (e.g., "Announcements", "Liturgy").
   - Attach the generated `.pro` or `.probundle` to that item.
3. **Credentials:** Use `.env` or the secrets directory as defined in `GEMINI.md`.

### Phase 5: Validation & Testing
1. **Verification Tool:** Create `utils/validate_output.py` to:
   - Decode `.pro` files to JSON/Text.
   - Check for uppercase compliance.
   - Verify font and palette usage.
2. **Regression:** Ensure the content parsing from `content_parser.py` (HTML/PDF) remains robust through the refactor.
