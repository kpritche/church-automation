# ProPresenter .pro and .probundle Files - Technical Reference

This guide provides technical documentation for working with ProPresenter 7 file formats. It covers binary structure, protocol buffer definitions, and common pitfalls when programmatically creating or modifying presentations.

Applicable to any project that needs to generate, read, or modify ProPresenter `.pro` or `.probundle` files.

## Overview

### .pro Files
- **Format**: Binary protocol buffer (protobuf) encoded files
- **Purpose**: Serialized ProPresenter presentation data structures
- **Root Message Type**: `Presentation` (from `presentation_pb2`)
- **Not Human Readable**: Must be decoded/deserialized using protobuf libraries

### .probundle Files
- **Format**: ZIP archive (ZIP_STORED, not compressed)
- **Contents**: 
  - Single `.pro` file (the presentation)
  - `Media/Assets/` directory with embedded media (images, QR codes, logos)
- **File Naming**: The .pro file inside matches the .probundle stem (e.g., `test.probundle` contains `test.pro`)
- **Archive Format**: ZIP64 with extended size fields when files exceed 4GB

## File Structure Details

### ZIP64 Considerations
ProPresenter templates use ZIP64 format with extended size fields in local file headers:
- **Extra field tag**: `0x0001` 
- **Extended size format**: 8-byte uncompressed and compressed sizes
- **Indicator**: File size shows as `0xFFFFFFFF` in standard ZIP fields
- **Solution**: Use `zipfile.ZipFile()` or implement manual ZIP64 parsing with `struct` module

### Probundle Internal Structure
```
test_announcements.probundle (ZIP)
├── test_announcements.pro (binary protobuf)
└── Media/
    └── Assets/
        ├── logo.png
        ├── announcement_1_image.png
        ├── announcement_1_qr.png
        ├── announcement_2_image.png
        ├── announcement_2_qr.png
        └── ...
```

## Protobuf Module Structure

### Generated Protobuf Files
ProPresenter 7 provides protocol buffer definitions that are compiled to Python modules. These are typically located in a `ProPresenter7_Proto/generated/` directory (or equivalent) in your project.

### Key Modules Required
- **Core**: `presentation_pb2`, `slide_pb2`, `cue_pb2`, `action_pb2`
- **Graphics**: `graphicsData_pb2` (contains `Graphics.Element`, `Graphics.Text`, etc.)
- **Types**: `basicTypes_pb2` (contains `UUID`, `Color`, `URL`)
- **Background**: `background_pb2`
- **Optional**: `uuid_pb2`, `url_pb2`, and others depending on use case

**Note**: You'll need the protobuf compiler and Python protobuf library to regenerate these if proto files change:
```bash
pip install protobuf
protoc --python_out=. *.proto
```

### Key Classes and Nested Structure

#### Presentation (`presentation_pb2.Presentation`)
- Root container for a ProPresenter show
- **Fields**:
  - `uuid`: UUID of presentation
  - `name`: Presentation name
  - `cues`: List of `Cue` objects (individual slides)
  - `cue_groups`: Groups of cues for organization
  - `background`: Background settings
  - `chord_chart`: Chord chart settings

#### Cue (`cue_pb2.Cue`)
- Represents a single slide/cue in the presentation
- **Fields**:
  - `uuid`: Unique identifier
  - `actions`: List of `Action` objects (usually one per cue)
  - `completion_action_type`: How to advance (default works fine)

#### Action (`action_pb2.Action`)
- Represents an action within a cue (typically a slide display)
- **Fields**:
  - `uuid`: Unique identifier
  - `type`: `ACTION_TYPE_PRESENTATION_SLIDE` for slide actions
  - `slide.presentation`: The actual `PresentationSlide` data

#### PresentationSlide (`presentationSlide_pb2.PresentationSlide`)
- The actual slide content
- **Fields**:
  - `base_slide`: Contains `elements` array
  - `base_slide.elements[]`: List of graphics elements

#### Graphics.Element (`graphicsData_pb2.Graphics.Element`)
- Individual graphic element on a slide (text, image, shape)
- **Fields**:
  - `uuid`: Element identifier
  - `name`: Element name (e.g., "title_text", "logo")
  - `bounds`: Position and size (origin.x/y, size.width/height)
  - `path`: Shape definition (rectangle, polygon, etc.)
  - `fill`: Fill properties (color, media/image, gradient)
  - `stroke`: Border/outline properties
  - `shadow`: Drop shadow settings
  - `text`: Text content and formatting (for text elements)
  - `opacity`: Transparency (0.0-1.0)
  - `aspect_ratio_locked`: Boolean

#### Graphics.Text (nested in Element)
- Text-specific properties
- **Fields**:
  - `rtf_data`: RTF formatted text as **bytes** (not string!)
  - `attributes`: Font, color, alignment settings
  - `vertical_alignment`: Top/Middle/Bottom
  - `shadow`: Text shadow
  - `is_superscript_standardized`: Boolean

#### Color (`basicTypes_pb2.Color`)
- Color representation
- **Fields** (all 0.0-1.0 normalized floats):
  - `red`: Red component
  - `green`: Green component
  - `blue`: Blue component
  - `alpha`: Opacity

#### UUID (`basicTypes_pb2.UUID`)
- Unique identifier
- **Fields**:
  - `string`: UUID as string (uppercase, e.g., "3B7A087D-BFEA-49E3-86BC-95B0271155BD")

## Common Pitfalls and Solutions

### 1. Field Name Conventions
**Problem**: Protobuf JSON uses camelCase, but Python protobuf generates snake_case
- **JSON**: `textSolidFill`, `absoluteString`, `completionActionType`
- **Python**: `text_solid_fill`, `absolute_string`, `completion_action_type`
**Solution**: Always use snake_case in Python code

### 2. Nested Enum References
**Problem**: Enums are nested in parent classes
- **Wrong**: `graphicsData_pb2.Shape.TYPE_RECTANGLE`
- **Correct**: `graphicsData_pb2.Graphics.Path.Shape.TYPE_RECTANGLE`
**Solution**: Check protobuf structure carefully, use proper nesting

### 3. RTF Data Must Be Bytes
**Problem**: `rtf_data` field expects bytes, not string
- **Wrong**: `element.text.rtf_data = "my rtf string"`
- **Correct**: `element.text.rtf_data = b"my rtf string"` or `rtf_string.encode('utf-8')`
**Solution**: Always encode RTF strings to UTF-8 bytes before assignment

### 4. Color Format Conversion
**Problem**: Settings store RGB as (0-255), protobuf needs normalized (0.0-1.0)
**Solution**: Use conversion function:
```python
def rgb_to_normalized(rgb_tuple: tuple[int, int, int]) -> tuple[float, float, float]:
    return (rgb_tuple[0]/255.0, rgb_tuple[1]/255.0, rgb_tuple[2]/255.0)
```

### 5. RTF Color Specification
**Problem**: RTF color references use color table indices and need proper encoding
**Key Points**:
- RTF uses `\colortbl` for color table definition
- Colors referenced with `\cf<index>` (e.g., `\cf2` for second color)
- CSS RGB format uses scaled values: `\cssrgb\c<scaled_r>\c<scaled_g>\c<scaled_b>` where scaled = value * 100000
- Example RTF color table:
  ```rtf
  {\colortbl;\red255\green255\blue255;\red56\green178\blue191;}
  {\*\expandedcolortbl;;\cssrgb\c22000\c70000\c62000;}
  ```

### 6. Element Info Field
**Problem**: Unknown purpose of `info` field on elements
**Status**: Optional, defaults work fine; not critical
- Observed value: `info = 2` or `info = 3` in template
- Can be omitted without breaking functionality

### 7. Clearing Collections
**Problem**: Can't use `.clear()` on protobuf repeated fields in Python 3.12+
- **Wrong**: `presentation.cues.clear()`
- **Correct**: `del presentation.cues[:]`
**Solution**: Use slice deletion syntax

### 8. Template Slide Structure
**Problem**: Understanding how to extract and reuse slide structures from existing presentations
**Key Pattern**: 
```python
# Load existing presentation as template
template_pres = presentation_pb2.Presentation()
template_pres.ParseFromString(template_bytes)

# Extract first slide
template_slide = template_pres.cues[0].actions[0].slide.presentation

# Use for new slides
new_slide = presentationSlide_pb2.PresentationSlide()
new_slide.CopyFrom(template_slide)
```
**Solution**: Always have a reference template file; extract and copy its structure rather than building from scratch

## RTF Generation

### RTF Structure for ProPresenter
```rtf
{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0
{\fonttbl\f0\fnil\fcharset0 FontName;}
{\colortbl;\red255\green255\blue255;\red56\green178\blue191;}
{\*\expandedcolortbl;;\cssrgb\c22000\c70000\c62000;}
\deftab1680
\pard\pardeftab1680\pardirnatural\ql\partightenfactor0
\f0\b\fs96 \cf2 \up0 My Title}
```

### Key RTF Codes
- `\rtf1`: RTF version 1
- `\ansi\ansicpg1252`: Character encoding
- `\cocoartf2822`: macOS Cocoa RTF version
- `\fonttbl`: Font table definition
- `\colortbl`: Color table definition
- `\f0`: Use font 0
- `\b`: Bold
- `\i`: Italic
- `\fs<n>`: Font size (half-points, so `\fs96` = 48pt)
- `\cf<n>`: Color foreground index
- `\ql`, `\qc`, `\qr`, `\qj`: Alignment (left, center, right, justify)
- `\par`: Paragraph break
- `\up0`: Baseline (0 = normal)

## Workflow for Creating Presentations

This is a general workflow for programmatically building ProPresenter presentations:

1. **Obtain Protobuf Modules**: Ensure you have the generated protobuf Python files in your path
2. **Load Template** (Optional but Recommended): Read an existing `.pro` file as bytes, deserialize to `Presentation`
   - This provides reference structure and ensures compatibility
3. **Create or Copy Presentation**: 
   - Option A: `presentation = presentation_pb2.Presentation()` (from scratch)
   - Option B: Copy template and modify
4. **Clear Default Content**: `del presentation.cues[:]` and `del presentation.cue_groups[:]`
5. **Create Cue Group**: Add cue group with UUID for organizing cues
6. **For Each Slide/Content Item**:
   - Create `PresentationSlide` (or copy from template)
   - Clear or populate elements: `del slide.base_slide.elements[:]`
   - Create elements: text boxes, images, shapes
   - Create `Cue` with UUID
   - Create `Action` with slide data
   - Add to presentation and cue group
7. **Finalize**: Set presentation name, UUID, metadata
8. **Serialize**: `presentation_data = presentation.SerializeToString()`
9. **Package**: 
   - Create ZIP file with `.pro` file
   - Include `Media/Assets/` directory with embedded media if needed
10. **Clean Up**: Remove temporary files

## Media File Handling

### Image Requirements
- **Format**: PNG recommended
- **Path in ZIP**: `Media/Assets/<filename>.png`
- **URL Reference**: `file://<filename>.png` (relative path in .pro file)
- **Metadata**: Store width and height in media element

### QR Code Generation
- Use `qrcode` library
- Save as PNG with `border=1, box_size=10`
- Store alongside other media files

### Logo Handling
- Copy from `LOGO_PATH` (in settings)
- Include in every presentation
- Reference as `Media/Assets/logo.png`

## Debugging Tips

1. **Decode Existing Files**: Build or use a decoder to inspect existing `.pro` or `.probundle` files
   - Export protobuf to JSON for human readability: `MessageToJson(message)`
   - Extract .probundle ZIP to examine structure
   - Compare against your generated files

2. **Use Reference Templates**: Always inspect official ProPresenter templates to understand expected structure

3. **Inspect Generated Output**: 
   - For .probundle: Extract the ZIP and examine the .pro file (binary, but JSON conversion helps)
   - For .pro: Deserialize and convert to JSON for inspection

4. **Validate Before Use**: 
   - Ensure all required UUIDs are present and properly formatted
   - Check that file paths in media references are correct
   - Verify RTF is properly encoded as bytes

5. **Test with ProPresenter**: Open generated files in ProPresenter to verify rendering

6. **Check Protobuf Errors**: Generated `_pb2.py` modules include error messages if you try to set wrong field types

## Quick Reference: Essential Patterns

### Generate a UUID
```python
import uuid
uuid_str = str(uuid.uuid4()).upper()
```

### Create Color (normalized 0.0-1.0 format)
```python
def create_color(r, g, b, alpha=1.0):
    c = basicTypes_pb2.Color()
    c.red, c.green, c.blue, c.alpha = r, g, b, alpha
    return c
```

### Convert RGB to normalized
```python
def rgb_to_normalized(rgb_tuple):  # (0-255)
    return tuple(v/255.0 for v in rgb_tuple)
```

### Create RTF text with custom color
```python
def generate_rtf_text(text, font_name, font_size, color_normalized=None):
    if color_normalized:
        r, g, b = [int(c * 255) for c in color_normalized]
        color_table = f"{{\\colortbl;\\red255\\green255\\blue255;\\red{r}\\green{g}\\blue{b};}}"
        color_ref = 2
    else:
        color_table = r"{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}"
        color_ref = 2
    
    rtf = f"{{\\rtf1\\ansi\\ansicpg1252\\cocoartf2822" \
          f"{{\\fonttbl\\f0\\fnil\\fcharset0 {font_name};}}" \
          f"{color_table}" \
          f"\\f0\\fs{font_size*2} \\cf{color_ref} {text}}}"
    return rtf.encode('utf-8')
```

### Create text element
```python
element = graphicsData_pb2.Graphics.Element()
element.uuid.CopyFrom(create_uuid_message(uuid_str))
element.name = "my_text"
element.bounds.origin.x, element.bounds.origin.y = 100, 100
element.bounds.size.width, element.bounds.size.height = 500, 100
element.text.rtf_data = generate_rtf_text("Hello", "Arial", 48)
element.text.vertical_alignment = graphicsData_pb2.Graphics.Text.VERTICAL_ALIGNMENT_MIDDLE
```

### Create image/media element
```python
element = graphicsData_pb2.Graphics.Element()
element.uuid.CopyFrom(create_uuid_message(uuid_str))
element.fill.enable = True
element.fill.media.url.absolute_string = "file://Media/Assets/image.png"
element.fill.media.url.platform = basicTypes_pb2.URL.Platform.PLATFORM_WIN32
element.fill.media.image.drawing.natural_size.width = 800
element.fill.media.image.drawing.natural_size.height = 600
```

### Serialize and save
```python
presentation_data = presentation.SerializeToString()

# Save as .pro
with open("presentation.pro", "wb") as f:
    f.write(presentation_data)

# Save as .probundle (ZIP)
with zipfile.ZipFile("presentation.probundle", 'w', zipfile.ZIP_STORED) as z:
    z.writestr("presentation.pro", presentation_data)
    z.write("path/to/image.png", "Media/Assets/image.png")
```

## Related Files and Resources

- **Protobuf Definitions**: Located in `ProPresenter7_Proto/proto/` or similar directory
- **Generated Protobuf Python**: In `ProPresenter7_Proto/generated/*.py` (auto-generated, don't edit)
- **ProPresenter Export**: Any existing .pro or .probundle file can be used as a template
- **Official Docs**: Check ProPresenter developer documentation for format specifications

### Implementation Examples
- **Generator**: Code that creates presentations programmatically
- **Decoder**: Code that reads and parses existing .pro or .probundle files
- **Converter**: Tools that transform between formats
