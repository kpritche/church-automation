#!/usr/bin/env python3
"""Compare image drawing metadata between two .pro files."""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, 'packages/slides/ProPresenter7_Proto/generated')
import presentation_pb2
from google.protobuf import text_format

GENERATED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")
CORRECTED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\2026-01-25\weekly_announcements_2026-01-25_mac\weekly_announcements_2026-01-25.pro")


def load_pro(path: Path):
    """Load a .pro file (handles both .pro and .probundle)."""
    pres = presentation_pb2.Presentation()
    
    if path.suffix.lower() == '.probundle':
        with zipfile.ZipFile(path, 'r') as z:
            pro_files = [f for f in z.namelist() if f.endswith('.pro')]
            if pro_files:
                with z.open(pro_files[0]) as f:
                    pres.ParseFromString(f.read())
    else:
        pres.ParseFromString(path.read_bytes())
    
    return pres


def print_detailed_media(media, name):
    """Print detailed media info including image drawing data."""
    print(f"  {name}:")
    print(f"    UUID: {media.uuid.string}")
    print(f"    absolute_string: {media.url.absolute_string}")
    
    if media.HasField('image'):
        print(f"    image:")
        if media.image.HasField('drawing'):
            d = media.image.drawing
            if d.HasField('natural_size'):
                print(f"      natural_size: {d.natural_size.width} x {d.natural_size.height}")
    else:
        print(f"    (no image field)")


def analyze(pres, cue_idx, label):
    print(f"\n{'='*60}")
    print(f"{label} - Cue {cue_idx}")
    print(f"{'='*60}")
    
    if cue_idx >= len(pres.cues):
        print("  Cue not found")
        return
    
    cue = pres.cues[cue_idx]
    for action in cue.actions:
        if action.HasField('slide') and action.slide.HasField('presentation'):
            slide = action.slide.presentation
            if slide.HasField('base_slide'):
                for ew in slide.base_slide.elements:
                    if ew.HasField('element'):
                        elem = ew.element
                        if elem.HasField('fill') and elem.fill.HasField('media'):
                            print_detailed_media(elem.fill.media, elem.name or "(unnamed)")


def main():
    gen_pres = load_pro(GENERATED)
    cor_pres = load_pro(CORRECTED)
    
    print(f"Generated: {len(gen_pres.cues)} cues")
    print(f"Corrected: {len(cor_pres.cues)} cues")
    
    # Compare first content cue (index 1 for generated, 0 for corrected)
    analyze(gen_pres, 1, "GENERATED")
    analyze(cor_pres, 0, "CORRECTED")


if __name__ == "__main__":
    main()
