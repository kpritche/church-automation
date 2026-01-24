#!/usr/bin/env python3
"""Detailed analysis of media references in generated bundle."""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, 'packages/slides/ProPresenter7_Proto/generated')
import presentation_pb2

BUNDLE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")


def main():
    print(f"Analyzing: {BUNDLE}")
    
    with zipfile.ZipFile(BUNDLE, 'r') as z:
        files = z.namelist()
        print(f"\nFiles in bundle ({len(files)}):")
        for f in sorted(files):
            print(f"  {f}")
        
        pro_files = [f for f in files if f.endswith('.pro')]
        if not pro_files:
            print("No .pro file found!")
            return
            
        with z.open(pro_files[0]) as f:
            pres = presentation_pb2.Presentation()
            pres.ParseFromString(f.read())
    
    print(f"\n{'='*70}")
    print(f"Presentation: {pres.name}")
    print(f"Total cues: {len(pres.cues)}")
    print(f"{'='*70}")
    
    for cue_idx, cue in enumerate(pres.cues):
        print(f"\n--- CUE {cue_idx} ---")
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
                                print(f"\n  Element '{name}':")
                                print(f"    media.uuid: {media.uuid.string}")
                                print(f"    url.absolute_string: {media.url.absolute_string}")
                                if media.url.HasField('local'):
                                    print(f"    url.local.path: {media.url.local.path}")
                                    print(f"    url.local.root: {media.url.local.root}")
                                    
                                    # Check if this file exists in bundle
                                    local_path = media.url.local.path
                                    filename = Path(local_path).name
                                    bundle_paths = [
                                        f"Media/{filename}",
                                        f"Media/Assets/{filename}",
                                        filename
                                    ]
                                    found = any(bp in files for bp in bundle_paths)
                                    status = "[OK] IN BUNDLE" if found else "[MISSING] NOT IN BUNDLE"
                                    print(f"    Status: {status}")


if __name__ == "__main__":
    main()
