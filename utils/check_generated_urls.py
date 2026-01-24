"""Check if URLs are properly set in the generated .pro file."""
import sys
from pathlib import Path
import zipfile

repo = Path(__file__).parent
sys.path.insert(0, str(repo / "packages" / "slides" / "ProPresenter7_Proto" / "generated"))

import presentation_pb2

bundle_path = repo / "packages" / "announcements" / "output" / "test_announcements.probundle"

print("Extracting and checking generated bundle...")
with zipfile.ZipFile(bundle_path, 'r') as z:
    pro_files = [n for n in z.namelist() if n.endswith('.pro')]
    if not pro_files:
        print("No .pro file found!")
        sys.exit(1)
    
    print(f"Found: {pro_files[0]}")
    
    # Extract and parse
    pro_data = z.read(pro_files[0])
    
p = presentation_pb2.Presentation()
p.ParseFromString(pro_data)

print(f"\nTotal cues: {len(p.cues)}")
print("\nChecking Cue 1 (First announcement):")

cue = p.cues[1]
slide = cue.actions[0].slide.presentation.base_slide

for i, elem_wrapper in enumerate(slide.elements):
    if elem_wrapper.HasField('element'):
        elem = elem_wrapper.element
        has_media = elem.HasField('fill') and elem.fill.HasField('media')
        
        if has_media:
            print(f"\nElement {i}: '{elem.name}'")
            media = elem.fill.media
            print(f"  Media UUID: {media.uuid.string}")
            if media.HasField('url'):
                print(f"  URL absolute: '{media.url.absolute_string}'")
                if media.url.HasField('local'):
                    print(f"  URL local: '{media.url.local.path}'")
                else:
                    print("  URL local: NOT SET")
            else:
                print("  URL: NOT SET AT ALL")
