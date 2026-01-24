"""Diagnostic script to inspect element names in announcement template.

This helps identify why media elements aren't being updated.
"""
import sys
from pathlib import Path

# Setup paths for proto imports
REPO_ROOT = Path(__file__).resolve().parent
PROTO_PATH = REPO_ROOT.parent.parent / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
if str(PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(PROTO_PATH))

import presentation_pb2

TEMPLATE_DIR = REPO_ROOT / "templates"
ANNOUNCEMENT_TEMPLATE = TEMPLATE_DIR / "announcement_template" / "announcement_template.pro"

def inspect_template():
    """Load template and print all element information."""
    print("=" * 70)
    print("TEMPLATE ELEMENT INSPECTOR")
    print("=" * 70)
    print(f"Template: {ANNOUNCEMENT_TEMPLATE}")
    print()
    
    if not ANNOUNCEMENT_TEMPLATE.exists():
        print(f"ERROR: Template not found at {ANNOUNCEMENT_TEMPLATE}")
        return
    
    # Load template (handles .probundle extraction)
    import zipfile
    import tempfile
    
    # Check if it's a .pro file directly
    if ANNOUNCEMENT_TEMPLATE.suffix.lower() == '.pro':
        pres = presentation_pb2.Presentation()
        with open(ANNOUNCEMENT_TEMPLATE, 'rb') as f:
            pres.ParseFromString(f.read())
    else:
        pres = presentation_pb2.Presentation()
        with open(ANNOUNCEMENT_TEMPLATE, 'rb') as f:
            pres.ParseFromString(f.read())
    
    print(f"Presentation: {pres.name}")
    print(f"Total cues: {len(pres.cues)}")
    print()
    
    if len(pres.cues) == 0:
        print("ERROR: No cues found in template")
        return
    
    # Inspect SECOND cue if available (first might be title slide)
    cue_idx = 1 if len(pres.cues) > 1 else 0
    template_cue = pres.cues[cue_idx]
    print(f"Inspecting Cue {cue_idx} (Template Slide)")
    print(f"  UUID: {template_cue.uuid.string}")
    print(f"  Actions: {len(template_cue.actions)}")
    print()
    
    if len(template_cue.actions) == 0:
        print("ERROR: No actions in template cue")
        return
    
    action = template_cue.actions[0]
    if not action.HasField('slide') or not action.slide.HasField('presentation'):
        print("ERROR: Action doesn't have slide presentation")
        return
    
    slide = action.slide.presentation
    if not slide.HasField('base_slide'):
        print("ERROR: No base_slide found")
        return
    
    elements = slide.base_slide.elements
    print(f"Total Elements: {len(elements)}")
    print("=" * 70)
    print()
    
    for idx, elem_wrapper in enumerate(elements):
        if elem_wrapper.HasField('element'):
            elem = elem_wrapper.element
            print(f"Element {idx}:")
            print(f"  Name: '{elem.name}'")
            print(f"  UUID: {elem.uuid.string}")
            
            # Check element type
            if elem.HasField('text'):
                # Try to decode RTF to see if it has placeholders
                try:
                    rtf_preview = elem.text.rtf_data.decode('utf-8', errors='ignore')[:200]
                    has_title = 'title_text' in rtf_preview
                    has_body = 'body_text' in rtf_preview
                    print(f"  Type: TEXT")
                    if has_title:
                        print(f"  Contains: TITLE PLACEHOLDER")
                    elif has_body:
                        print(f"  Contains: BODY PLACEHOLDER")
                except:
                    print(f"  Type: TEXT (couldn't decode RTF)")
            
            elif elem.HasField('fill') and elem.fill.HasField('media'):
                print(f"  Type: MEDIA")
                media = elem.fill.media
                print(f"  Media UUID: {media.uuid.string}")
                
                if media.HasField('url'):
                    print(f"  Absolute Path: {media.url.absolute_string}")
                    if media.url.HasField('local'):
                        print(f"  Local Path: {media.url.local.path}")
                
                if media.HasField('metadata'):
                    print(f"  Format: {media.metadata.format}")
                
                # Check if dimensions are set
                if media.HasField('image') and media.image.HasField('drawing'):
                    nat_size = media.image.drawing.natural_size
                    print(f"  Dimensions: {nat_size.width} x {nat_size.height}")
            
            else:
                print(f"  Type: OTHER")
            
            print()
    
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    # Count element types
    text_count = 0
    media_count = 0
    media_names = []
    
    for elem_wrapper in elements:
        if elem_wrapper.HasField('element'):
            elem = elem_wrapper.element
            if elem.HasField('text'):
                text_count += 1
            elif elem.HasField('fill') and elem.fill.HasField('media'):
                media_count += 1
                media_names.append(elem.name)
    
    print(f"Text elements: {text_count}")
    print(f"Media elements: {media_count}")
    print(f"Media element names: {', '.join([repr(n) for n in media_names])}")
    print()
    print("TIP: Look for media elements that should be updated with")
    print("     dynamic content (QR codes, images). Note their exact names.")
    print()

if __name__ == "__main__":
    inspect_template()
