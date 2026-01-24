#!/usr/bin/env python3
"""Compare two ProPresenter bundles to find differences in media references."""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, 'packages/slides/ProPresenter7_Proto/generated')
import presentation_pb2
from google.protobuf import text_format

CORRECTED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\templates\weekly_announcements_2026-01-25_corrected.proBundle")
GENERATED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")


def extract_media_info(bundle_path: Path):
    """Extract media reference info from a bundle."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {bundle_path.name}")
    print(f"{'='*60}")
    
    with zipfile.ZipFile(bundle_path, 'r') as z:
        file_list = z.namelist()
        print(f"\nFiles in bundle ({len(file_list)} total):")
        for f in file_list:
            print(f"  - {f}")
        
        pro_files = [f for f in z.namelist() if f.endswith('.pro')]
        if not pro_files:
            print("No .pro file found!")
            return
        
        with z.open(pro_files[0]) as f:
            pres = presentation_pb2.Presentation()
            pres.ParseFromString(f.read())
        
        print(f"\nPresentation: {pres.name}")
        print(f"Total cues: {len(pres.cues)}")
        
        for cue_idx, cue in enumerate(pres.cues):
            print(f"\n--- Cue {cue_idx + 1} ---")
            for action in cue.actions:
                if action.HasField('slide') and action.slide.HasField('presentation'):
                    slide = action.slide.presentation
                    if slide.HasField('base_slide'):
                        for elem_wrapper in slide.base_slide.elements:
                            if elem_wrapper.HasField('element'):
                                elem = elem_wrapper.element
                                name = elem.name if elem.name else "(unnamed)"
                                
                                if elem.HasField('fill') and elem.fill.HasField('media'):
                                    media = elem.fill.media
                                    print(f"\n  Element: {name}")
                                    print(f"    UUID: {media.uuid.string}")
                                    print(f"    absolute_string: {media.url.absolute_string}")
                                    if media.url.HasField('local'):
                                        print(f"    local.path: {media.url.local.path}")
                                    print(f"    metadata.format: {media.metadata.format if media.HasField('metadata') else 'N/A'}")
                                    
                                    # Print the full URL message for debugging
                                    print(f"    Full URL proto: {media.url}")


if __name__ == "__main__":
    if CORRECTED.exists():
        extract_media_info(CORRECTED)
    else:
        print(f"Corrected bundle not found: {CORRECTED}")
    
    print("\n" + "="*80 + "\n")
    
    if GENERATED.exists():
        extract_media_info(GENERATED)
    else:
        print(f"Generated bundle not found: {GENERATED}")
