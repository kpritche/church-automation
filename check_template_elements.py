#!/usr/bin/env python3
"""Check element names in template."""
import sys
from pathlib import Path

sys.path.insert(0, 'packages/slides/ProPresenter7_Proto/generated')
import presentation_pb2

TEMPLATE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\templates\announcement_template_mac\announcement_template.pro")

pres = presentation_pb2.Presentation()
pres.ParseFromString(TEMPLATE.read_bytes())

print(f"Template: {TEMPLATE.name}")
print(f"Total cues: {len(pres.cues)}")

for cue_idx, cue in enumerate(pres.cues):
    print(f"\n--- CUE {cue_idx} ---")
    for action in cue.actions:
        if action.HasField('slide') and action.slide.HasField('presentation'):
            slide = action.slide.presentation
            if slide.HasField('base_slide'):
                for i, ew in enumerate(slide.base_slide.elements):
                    if ew.HasField('element'):
                        elem = ew.element
                        name = repr(elem.name) if elem.name else "(empty)"
                        has_media = "MEDIA" if (elem.HasField('fill') and elem.fill.HasField('media')) else ""
                        print(f"  [{i}] name={name:20} {has_media}")
                        if has_media:
                            media = elem.fill.media
                            # Extract just filename from path
                            local_path = media.url.local.path if media.url.HasField('local') else ""
                            filename = Path(local_path).name if local_path else ""
                            print(f"       -> local.path filename: {filename}")
