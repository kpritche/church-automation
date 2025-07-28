# use_template.py
"""
Programmatically generate ProPresenter .pro slides by cloning a template and replacing only the text and text color.

Usage:
  python use_template.py --template template.txt --output_dir output_slides

Requirements:
  • `protobuf` Python package
  • Generated Python modules from your `.proto` definitions (presentation_pb2, cue_pb2, action_pb2, slide_pb2, presentationSlide_pb2, graphicsData_pb2) in a `generated` folder on PYTHONPATH
"""
import os
import sys
import uuid
from argparse import ArgumentParser
from google.protobuf.message import DecodeError
from google.protobuf import text_format

# 1) Ensure generated modules are in import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ProPresenter7_Proto', 'generated'))

# 2) Import generated protobuf classes
import ProPresenter7_Proto.generated.presentation_pb2 as rv_presentation
import ProPresenter7_Proto.generated.cue_pb2         as rv_cue
import ProPresenter7_Proto.generated.action_pb2      as rv_action
import ProPresenter7_Proto.generated.presentationSlide_pb2 as rv_pslide
import ProPresenter7_Proto.generated.slide_pb2       as rv_slide
import ProPresenter7_Proto.generated.graphicsData_pb2 as rv_graphics

# Aliases
Presentation      = rv_presentation.Presentation
Action            = rv_action.Action
PresentationSlide = rv_pslide.PresentationSlide

# Determine presentation-slide action enum value
try:
    ACTION_PRESENT_SLIDE = rv_action.ActionType.ACTION_TYPE_PRESENTATION_SLIDE
except AttributeError:
    ACTION_PRESENT_SLIDE = rv_action.Action.ActionType.ACTION_TYPE_PRESENTATION_SLIDE

# Standard 8-byte footer for .pro files
FOOTER = b"\x00" * 8


def load_template(path: str) -> Presentation:
    """Load a template in either text-proto (.txt) or binary .pro format."""
    pres = Presentation()
    if path.lower().endswith('.txt'):
        # parse text-format proto
        with open(path, 'r', encoding='utf-8') as f:
            text_format.Merge(f.read(), pres)
    else:
        # binary .pro
        data = open(path, 'rb').read()
        body = data[:-len(FOOTER)] if data.endswith(FOOTER) else data
        pres.ParseFromString(body)
    return pres


def write_pro(pres: Presentation, out_path: str):
    """Serialize a Presentation back to a .pro file."""
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(pres.SerializeToString() + FOOTER)


def update_slide_from_template(pres: Presentation, new_text: str, rgb: tuple[float, float, float]):
    """
    Mutate the cloned Presentation in-place:
      - For each presentation-slide action, update element's text.rtf_data and text_solid_fill color.
    """
    for cue in pres.cues:
        for action in cue.actions:
            if action.type != ACTION_PRESENT_SLIDE:
                continue
            # get base slide
            base = action.slide.presentation.base_slide
            # assume first element is the text container
            if not base.elements:
                continue
            elem_wrap = base.elements[0]
            elem = elem_wrap.element
            # update color attribute
            attr = elem.text.attributes
            attr.text_solid_fill.red   = rgb[0]
            attr.text_solid_fill.green = rgb[1]
            attr.text_solid_fill.blue  = rgb[2]
            attr.text_solid_fill.alpha = 1.0
            # build simple RTF payload preserving existing font and RTF header
            # naive: extract prefix up to the first space
            rtf = elem.text.rtf_data.decode('utf-8')
            # header, _, _ = rtf.partition('}')
            header = "{\\rtf0\\ansi\\ansicpg1252{\\fonttbl\\f0\\fnil HelveticaNeue-Bold;}{\\colortbl;\\red255\\green255\\blue255;\\red255\\green255\\blue255;}{\\*\\expandedcolortbl;\\csgenericrgb\\c100000\\c100000\\c100000\\c100000;\\csgenericrgb\\c100000\\c100000\\c100000\\c0;}{\\*\\listtable}{\\*\\listoverridetable}\\uc1\\paperw12240\\margl0\\margr0\\margt0\\margb0\\pard\\li0\\fi0\\ri0\\qc\\sb0\\sa0\\sl20\\slmult0\\slleading0\\f0\\b\\i0\\ul0\\strike0\\fs160\\expnd0\\expndtw0\\CocoaLigature0\\cf1\\strokewidth0\\strokec1\\nosupersub\\ulc0\\highlight2\\cb2 "
            new_rtf = f"{header}{new_text}"
            new_rtf += r'}'
            elem.text.rtf_data = new_rtf.encode('utf-8')
    return pres


def main():
    p = ArgumentParser()
    p.add_argument('--template', required=True, help='Path to template.txt or .pro')
    p.add_argument('--output_dir', required=True, help='Directory for generated .pro slides')
    args = p.parse_args()

    template = load_template(args.template)
    # Example items; replace with your Planning Center data
    items = [
        {'text': 'First slide content', 'color': (1.0, 0.0, 0.0)},
        {'text': 'Second slide content', 'color': (0.0, 1.0, 0.0)},
    ]

    for idx, item in enumerate(items, start=1):
        clone = Presentation()
        clone.CopyFrom(template)
        clone.uuid.string = str(uuid.uuid4())
        clone.name = f"slide_{idx}"
        update_slide_from_template(clone, item['text'], item['color'])
        out_path = os.path.join(args.output_dir, f"slide_{idx}.pro")
        write_pro(clone, out_path)
        print(f"Wrote: {out_path}")

    

if __name__ == '__main__':
    main()
