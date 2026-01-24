"""Check template media elements."""
import sys
from pathlib import Path

repo = Path(__file__).parent
sys.path.insert(0, str(repo / "packages" / "slides" / "ProPresenter7_Proto" / "generated"))

import presentation_pb2

template_path = repo / "packages" / "announcements" / "templates" / "announcement_template" / "announcement_template.pro"

p = presentation_pb2.Presentation()
with open(template_path, 'rb') as f:
    p.ParseFromString(f.read())

print("Template Elements:")
for i, elem_wrapper in enumerate(p.cues[0].actions[0].slide.presentation.base_slide.elements):
    if elem_wrapper.HasField('element'):
        elem = elem_wrapper.element
        has_media = elem.HasField('fill') and elem.fill.HasField('media')
        print(f"  {i}: name='{elem.name}' has_media={has_media}")
        
        if has_media:
            media = elem.fill.media
            print(f"     Media UUID: {media.uuid.string}")
            if media.HasField('url'):
                print(f"     URL absolute: '{media.url.absolute_string}'")
                if media.url.HasField('local'):
                    print(f"     URL local: '{media.url.local.path}'")
