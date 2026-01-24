"""Inspect a working generated bundle to see the media element structure."""
import sys
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent
PROTO_PATH = REPO_ROOT.parent.parent / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
if str(PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(PROTO_PATH))

import presentation_pb2
import py7zr
import tempfile

WORKING_BUNDLE = REPO_ROOT.parent.parent / "packages" / "announcements" / "output" / "2026-01-25" / "weekly_announcements_2026-01-25_mac.probundle"

print("=" * 70)
print("WORKING BUNDLE INSPECTOR")
print("=" * 70)
print(f"Bundle: {WORKING_BUNDLE}")
print()

with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    
    # Extract bundle
    with py7zr.SevenZipFile(WORKING_BUNDLE, 'r') as z:
        z.extractall(temp_path)
    
    # Find .pro file
    pro_files = list(temp_path.rglob('*.pro'))
    if not pro_files:
        print("ERROR: No .pro file found")
        sys.exit(1)
    
    print(f"Found .pro file: {pro_files[0].name}")
    
    # Load presentation
    pres = presentation_pb2.Presentation()
    with open(pro_files[0], 'rb') as f:
        pres.ParseFromString(f.read())
    
    print(f"Total cues: {len(pres.cues)}")
    print()
    
    # Inspect cue 1 (should have full announcement layout)
    if len(pres.cues) < 2:
        print("ERROR: Not enough cues in bundle")
        sys.exit(1)
    
    cue = pres.cues[1]
    action = cue.actions[0]
    slide = action.slide.presentation.base_slide
    
    print(f"Inspecting Cue 1 (First Announcement Slide)")
    print(f"Total Elements: {len(slide.elements)}")
    print("=" * 70)
    print()
    
    for i, elem_wrapper in enumerate(slide.elements):
        if elem_wrapper.HasField('element'):
            elem = elem_wrapper.element
            
            is_media = elem.HasField('fill') and elem.fill.HasField('media')
            elem_type = "MEDIA" if is_media else ("TEXT" if elem.HasField('text') else "OTHER")
            
            print(f"Element {i}:")
            print(f"  Name: '{elem.name}'")
            print(f"  Type: {elem_type}")
            
            if is_media:
                media = elem.fill.media
                print(f"  Media UUID: {media.uuid.string}")
                if media.HasField('url'):
                    print(f"  Absolute: {media.url.absolute_string}")
                    if media.url.HasField('local'):
                        print(f"  Local: {media.url.local.path}")
                if media.HasField('metadata'):
                    print(f"  Format: {media.metadata.format}")
            print()
    
    print("=" * 70)
    print("This shows what your TEMPLATE should look like!")
    print("=" * 70)
