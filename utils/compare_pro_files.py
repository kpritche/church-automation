#!/usr/bin/env python3
"""Compare two ProPresenter .pro files to find differences."""
import sys
from pathlib import Path

sys.path.insert(0, 'packages/slides/ProPresenter7_Proto/generated')
import presentation_pb2
from google.protobuf import text_format

GENERATED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\2026-01-25\weekly_announcements_2026-01-25 copy\weekly_announcements_2026-01-25.pro")
CORRECTED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\2026-01-25\weekly_announcements_2026-01-25_mac\weekly_announcements_2026-01-25.pro")


def load_pro(path: Path):
    """Load a .pro file."""
    pres = presentation_pb2.Presentation()
    pres.ParseFromString(path.read_bytes())
    return pres


def print_media_info(media, prefix=""):
    """Print detailed media info."""
    print(f"{prefix}UUID: {media.uuid.string}")
    print(f"{prefix}URL:")
    print(f"{prefix}  platform: {media.url.platform}")
    print(f"{prefix}  absolute_string: {media.url.absolute_string}")
    if media.url.HasField('local'):
        print(f"{prefix}  local.root: {media.url.local.root}")
        print(f"{prefix}  local.path: {media.url.local.path}")
    if media.HasField('metadata'):
        print(f"{prefix}  metadata: {media.metadata}")


def analyze_slide(pres, cue_index):
    """Analyze a specific cue/slide."""
    if cue_index >= len(pres.cues):
        print(f"  No cue at index {cue_index}")
        return
    
    cue = pres.cues[cue_index]
    print(f"  Cue UUID: {cue.uuid.string}")
    
    for action_idx, action in enumerate(cue.actions):
        print(f"  Action {action_idx}: UUID={action.uuid.string}")
        
        if action.HasField('slide') and action.slide.HasField('presentation'):
            slide = action.slide.presentation
            if slide.HasField('base_slide'):
                print(f"    Base slide UUID: {slide.base_slide.uuid.string}")
                
                for elem_idx, elem_wrapper in enumerate(slide.base_slide.elements):
                    if elem_wrapper.HasField('element'):
                        elem = elem_wrapper.element
                        name = elem.name if elem.name else "(unnamed)"
                        print(f"\n    Element {elem_idx}: '{name}'")
                        print(f"      UUID: {elem.uuid.string}")
                        
                        if elem.HasField('fill') and elem.fill.HasField('media'):
                            print(f"      Media fill:")
                            print_media_info(elem.fill.media, "        ")


def main():
    print("="*80)
    print("GENERATED FILE (first slide)")
    print("="*80)
    gen_pres = load_pro(GENERATED)
    print(f"Name: {gen_pres.name}")
    print(f"Total cues: {len(gen_pres.cues)}")
    # Cue 0 is usually blank, cue 1 is first content slide
    analyze_slide(gen_pres, 1)
    
    print("\n" + "="*80)
    print("CORRECTED FILE (only slide)")
    print("="*80)
    cor_pres = load_pro(CORRECTED)
    print(f"Name: {cor_pres.name}")
    print(f"Total cues: {len(cor_pres.cues)}")
    analyze_slide(cor_pres, 0)
    
    # Also print raw text format for deep comparison
    print("\n" + "="*80)
    print("RAW TEXT FORMAT - GENERATED FIRST SLIDE")
    print("="*80)
    if len(gen_pres.cues) > 1:
        print(text_format.MessageToString(gen_pres.cues[1], as_utf8=True)[:5000])
    
    print("\n" + "="*80)
    print("RAW TEXT FORMAT - CORRECTED SLIDE")
    print("="*80)
    if len(cor_pres.cues) > 0:
        print(text_format.MessageToString(cor_pres.cues[0], as_utf8=True)[:5000])


if __name__ == "__main__":
    main()
