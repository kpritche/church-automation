#!/usr/bin/env python3
"""Check what media URLs are in the template before generation."""

import sys
from pathlib import Path

# Add proto path
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTO_PATH = _REPO_ROOT / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
if str(_PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(_PROTO_PATH))

import presentation_pb2

TEMPLATE_PATH = Path(__file__).parent / "templates" / "announcement_template" / "announcement_template.pro"

with open(TEMPLATE_PATH, 'rb') as f:
    pres = presentation_pb2.Presentation()
    pres.ParseFromString(f.read())

print(f"Template: {TEMPLATE_PATH.name}\n")

cue = pres.cues[0]
print(f"Checking cue: {cue.uuid.string}")

slide = cue.actions[0].slide.presentation.base_slide
print(f"Total elements: {len(slide.elements)}\n")

for i, elem_wrapper in enumerate(slide.elements):
    elem = elem_wrapper.element
    
    if elem.HasField('fill') and elem.fill.HasField('media'):
        media = elem.fill.media
        print(f"Element {i}: '{elem.name}'")
        print(f"  Media UUID: {media.uuid.string}")
        print(f"  URL absolute: '{media.url.absolute_string}'")
        print(f"  URL local: '{media.url.local.path}'")
        print()
