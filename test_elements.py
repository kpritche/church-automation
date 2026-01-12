#!/usr/bin/env python3
import sys
import zipfile
sys.path.insert(0, 'packages/slides/ProPresenter7_Proto/generated')
import presentation_pb2

prob_file = r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\2026-01-11\weekly_announcements_2026-01-11.probundle"

try:
    with zipfile.ZipFile(prob_file, 'r') as z:
        pro_files = [f for f in z.namelist() if f.endswith('.pro')]
        if pro_files:
            with z.open(pro_files[0]) as f:
                pres = presentation_pb2.Presentation()
                pres.ParseFromString(f.read())
                
                print(f"Total cues: {len(pres.cues)}")
                for i, cue in enumerate(pres.cues):
                    if cue.actions:
                        slide = cue.actions[0].slide.presentation
                        empty_count = 0
                        for elem_wrapper in slide.base_slide.elements:
                            elem = elem_wrapper.element
                            if not elem.HasField('text') and not elem.HasField('fill'):
                                empty_count += 1
                        print(f"Cue {i+1}: {len(slide.base_slide.elements)} elements, {empty_count} empty")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
