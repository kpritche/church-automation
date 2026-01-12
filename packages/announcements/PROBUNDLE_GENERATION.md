# ProPresenter .probundle Generator - Technical Documentation

## Overview

This module generates ProPresenter `.probundle` files from announcement data using Protocol Buffers. It serves the same function as `ppt_generator.py` but outputs ProPresenter's native format instead of PowerPoint.

## Architecture

### What is a .probundle?

A `.probundle` is a ZIP archive containing:
```
example_announcements.probundle/
├── example_announcements.pro    # Serialized protobuf (Presentation message)
└── Media/
    └── Assets/
        ├── logo.png
        ├── announcement_1_image.png
        ├── announcement_1_qr.png
        ├── announcement_2_image.png
        └── announcement_2_qr.png
```

### Key Components

1. **probundle_generator.py** - Core generator with slide factory functions
2. **Protocol Buffers** - Schema definitions in `packages/slides/ProPresenter7_Proto/proto/`
3. **Generated Python modules** - In `packages/slides/ProPresenter7_Proto/generated/`

## Protocol Buffer Compilation

### Prerequisites

```powershell
# Install protobuf compiler
# Download from: https://github.com/protocolbuffers/protobuf/releases

# Or use Chocolatey on Windows:
choco install protoc

# Or pip install:
pip install protobuf
```

### Compilation Command

```powershell
# From repo root
cd packages/slides/ProPresenter7_Proto

# Compile all .proto files
protoc -I="proto" `
  --python_out="generated" `
  proto/*.proto

# Or use the included protoc binary:
.\protoc-27.5-win64\bin\protoc.exe -I="proto" `
  --python_out="generated" `
  proto/*.proto
```

### Generated Files

This creates Python modules in `generated/`:
- `presentation_pb2.py` - Main presentation structure
- `cue_pb2.py` - Cue and timeline definitions
- `action_pb2.py` - Action types
- `slide_pb2.py` - Slide elements
- `graphicsData_pb2.py` - Colors, paths, shapes
- `basicTypes_pb2.py` - UUID, timestamps, etc.
- And more...

## Critical Implementation Details

### 1. UUID Regeneration (MOST IMPORTANT!)

ProPresenter links elements by UUID. **Every UUID must be unique** or editing one slide will affect all slides.

```python
def regenerate_all_uuids(obj: Any) -> None:
    """
    Recursively traverse a protobuf message and regenerate all UUID fields.
    
    CRITICAL: If you skip this, all slides will be linked together!
    """
    if hasattr(obj, 'DESCRIPTOR'):
        for field in obj.DESCRIPTOR.fields:
            if field.name == 'uuid' and hasattr(obj, 'uuid'):
                if hasattr(obj.uuid, 'string'):
                    obj.uuid.string = str(uuid.uuid4()).upper()
            
            # Recurse into nested messages...
```

### 2. RTF Text Encoding

Text elements use RTF (Rich Text Format) encoding:

```python
def generate_rtf_text(text: str, font_name: str = "SourceSansPro-Bold", 
                      font_size: int = 48, bold: bool = False, 
                      italic: bool = False, alignment: str = "left", 
                      color: tuple[float, float, float] = None) -> bytes:
    """Generate RTF formatted text and return as bytes."""
    
    # RTF structure
    rtf = (
        r"{\rtf1\ansi\ansicpg1252\cocoartf2822"
        r"\cocoatextscaling0\cocoaplatform0"
        r"{\fonttbl\f0\fnil\fcharset0 " + font_name + r";}"
        # ... color table, text, etc ...
        r"}"
    )
    
    return rtf.encode('utf-8')
```

**Important:** The RTF is stored as raw bytes in `element.text.rtf_data`, NOT base64 encoded.

### 3. Template Loading

Two approaches:

#### A. From Binary .pro File (Used in Production)

```python
with open("template.pro", 'rb') as f:
    template_data = f.read()

template_pres = presentation_pb2.Presentation()
template_pres.ParseFromString(template_data)
```

#### B. From JSON (Alternative)

```python
from google.protobuf import json_format

with open("template.json", 'r') as f:
    json_data = f.read()

template_pres = json_format.Parse(json_data, presentation_pb2.Presentation())
```

### 4. Slide Factory Pattern

```python
def create_announcement_slide(announcement: dict, slide_index: int, 
                              media_dir: Path, template_slide: Any) -> tuple[Any, list]:
    """
    Create a slide for an announcement.
    
    Returns:
        Tuple of (slide_proto, list of media files to include)
    """
    # 1. Deep copy template
    slide = presentationSlide_pb2.PresentationSlide()
    slide.CopyFrom(template_slide)
    
    # 2. Regenerate slide UUID
    slide.base_slide.uuid.CopyFrom(create_uuid_message(generate_uuid()))
    
    # 3. Clear template elements
    del slide.base_slide.elements[:]
    
    # 4. Create new elements
    media_files = []
    
    # Title element
    title_element = create_text_element(
        text=announcement["title"],
        element_uuid=generate_uuid(),
        element_name="title_text",
        bounds_x=50, bounds_y=0, bounds_w=1820, bounds_h=275,
        font_name="SourceSansPro-Black",
        font_size=84,
        bold=True
    )
    
    slide_element = slide.base_slide.elements.add()
    slide_element.element.CopyFrom(title_element)
    slide_element.info = 3  # Layer/z-index
    
    # ... more elements (body, image, QR, logo) ...
    
    return slide, media_files
```

### 5. Creating the .probundle

```python
def create_probundle(announcements: list[dict], output_path: Path) -> None:
    # 1. Load template
    template_pres = load_template()
    
    # 2. Create new presentation
    presentation = presentation_pb2.Presentation()
    presentation.CopyFrom(template_pres)
    
    # 3. Clear existing cues
    del presentation.cues[:]
    del presentation.cue_groups[:]
    
    # 4. Create cue group
    cue_group = presentation.cue_groups.add()
    
    # 5. Create slides
    for idx, announcement in enumerate(announcements):
        slide, media_files = create_announcement_slide(announcement, idx, ...)
        
        # Create cue
        cue = presentation.cues.add()
        cue.uuid.CopyFrom(create_uuid_message(generate_uuid()))
        
        # Add action
        action = cue.actions.add()
        action.type = action_pb2.Action.ACTION_TYPE_PRESENTATION_SLIDE
        action.slide.presentation.CopyFrom(slide)
        
        # Add to cue group
        cue_group.cue_identifiers.add().string = cue.uuid.string
    
    # 6. Serialize to bytes
    presentation_data = presentation.SerializeToString()
    
    # 7. Create ZIP file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zipf:
        zipf.writestr(f"{output_path.stem}.pro", presentation_data)
        for zip_path, file_path in all_media_files:
            zipf.write(file_path, zip_path)
```

## Element Positioning

ProPresenter uses a coordinate system with origin at top-left:

```
(0,0) ────────────────────────────► X (1920)
  │
  │   ┌─────────────────────────┐
  │   │  Title (50, 0)          │
  │   ├─────────┬───────────────┤
  │   │ Body    │ Image         │
  │   │ (50,265)│ (1250, 275)   │
  │   │         │               │
  │   ├─────────┼───────────────┤
  │   │ Logo    │ QR Code       │
  │   │ (0,864) │ (781, 619)    │
  │   └─────────┴───────────────┘
  ▼
  Y (1080)
```

### Standard Element Positions

| Element | X | Y | Width | Height |
|---------|---|---|-------|--------|
| Title | 50 | 0 | 1820 | 275 |
| Body | 50 | 265 | 1150 | 375 |
| Logo | 0 | 864 | 729 | 216 |
| Image | 1250 | 275 | 620 | 755 |
| QR Code | 781 | 619 | 395 | 395 |
| QR Text | 710 | 1014 | 538 | 39 |

## Usage Examples

### Example 1: Basic Usage

```python
from announcements_app.probundle_generator import create_probundle
from pathlib import Path

announcements = [
    {
        "title": "Welcome!",
        "body": "Join us this Sunday.",
        "link": "https://example.com",
        "button_text": "Learn More",
        "image_url": "https://example.com/image.jpg"
    }
]

output_path = Path("output/announcements.probundle")
create_probundle(announcements, output_path)
```

### Example 2: With Gmail Integration

```python
from announcements_app.gmail_utils import authenticate_gmail, fetch_latest_announcement_html
from announcements_app.html_parser import parse_announcements
from announcements_app.probundle_generator import create_probundle

# Fetch from Gmail
service = authenticate_gmail()
html_content = fetch_latest_announcement_html(service)
announcements = parse_announcements(html_content)

# Generate .probundle
create_probundle(announcements, output_path)
```

### Example 3: Standalone Script

See `examples/generate_probundle_example.py` for a complete, runnable example.

## Debugging

### Inspect .probundle Contents

```python
import zipfile

with zipfile.ZipFile('announcements.probundle', 'r') as zipf:
    zipf.printdir()
    
    # Extract .pro file
    with zipf.open('announcements.pro') as f:
        pro_data = f.read()
    
    # Parse protobuf
    import presentation_pb2
    pres = presentation_pb2.Presentation()
    pres.ParseFromString(pro_data)
    
    print(f"Name: {pres.name}")
    print(f"Cues: {len(pres.cues)}")
```

### Decode RTF Data

```python
rtf_bytes = element.text.rtf_data
rtf_string = rtf_bytes.decode('utf-8')
print(rtf_string)
# Output: {\rtf1\ansi...}
```

### Export to JSON for Inspection

```python
from google.protobuf import json_format

pres = presentation_pb2.Presentation()
pres.ParseFromString(pro_data)

json_str = json_format.MessageToJson(pres, indent=2)
with open('debug.json', 'w') as f:
    f.write(json_str)
```

## Common Issues

### Issue 1: Slides Are Linked Together

**Problem:** Editing one slide in ProPresenter changes all slides.

**Solution:** You didn't regenerate UUIDs. Every UUID must be unique.

```python
# WRONG - reusing template UUIDs
slide.CopyFrom(template_slide)

# CORRECT - regenerate all UUIDs
slide.CopyFrom(template_slide)
regenerate_all_uuids(slide)
```

### Issue 2: Text Not Displaying

**Problem:** RTF data is malformed or missing.

**Solution:** Ensure RTF is properly encoded as UTF-8 bytes.

```python
# CORRECT
element.text.rtf_data = generate_rtf_text("Hello", "Arial", 48)

# WRONG - string instead of bytes
element.text.rtf_data = "{\rtf1...}"
```

### Issue 3: Images Not Loading

**Problem:** File paths are incorrect or files missing from ZIP.

**Solution:** Use relative paths in protobuf, ensure files are added to ZIP.

```python
# In protobuf
element.fill.media.url.relative_path = "Media/Assets/image.png"

# In ZIP
zipf.write(local_path, "Media/Assets/image.png")
```

## Performance Considerations

- **Image sizes:** ProPresenter handles images well, but keep under 2MB per image
- **QR codes:** Generated at 10px box size for good scanning
- **RTF complexity:** Keep formatting simple for better performance
- **Slide count:** No practical limit, but 20-30 slides per probundle is typical

## Platform Compatibility

The generator creates Mac-compatible files by default:

```python
app_info.platform = basicTypes_pb2.ApplicationInfo.Platform.PLATFORM_MACOS
app_info.platform_version.major_version = 15  # macOS Sequoia
app_info.application_version.major_version = 19  # ProPresenter 7.19
```

These files work on **both Mac and Windows** versions of ProPresenter.

## Further Reading

- ProPresenter Protocol Buffers: `packages/slides/ProPresenter7_Proto/README.md`
- Protocol Buffers Python Tutorial: https://protobuf.dev/getting-started/pythontutorial/
- ProPresenter API Documentation: https://renewedvision.com/propresenter/

## License

This code is part of the Church Automation suite. See LICENSE for details.
