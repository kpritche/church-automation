# pro_generator.py
"""Pure‑Python port of ProPresenter C# sample: read/write *.pro and build a demo presentation

This script:
  • Reads an existing .pro file (strips/appends the 8‑byte footer).
  • Constructs a new Presentation in memory (two slides, a group, an arrangement).
  • Writes it back to disk as a .pro.

Usage:
  python pro_generator.py [--template path/to/your.pro]
"""
from __future__ import annotations
import sys, os
# Ensure generated modules are on the path for bare imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ProPresenter7_Proto', 'generated'))

import os
import sys
import uuid
from google.protobuf.message import DecodeError

# ──────────────────────────────────────────────────────────────────────────────
#  Imports of generated protobuf modules (bare imports require sys.path fix above)
# ──────────────────────────────────────────────────────────────────────────────
try:
    import presentation_pb2 as rv_presentation
    import cue_pb2         as rv_cue
    import action_pb2      as rv_action
    import presentationSlide_pb2 as rv_pslide
    import slide_pb2       as rv_slide
    import graphicsData_pb2 as rv_graphics
except ImportError as e:
    sys.stderr.write(
        "❌  Could not import generated modules via bare import."
        "    Ensure you inserted the correct sys.path above pointing to the 'generated' folder."
        f"    ({e})"
    )
    raise
#  Dynamic imports of user‑generated protobuf modules
# ──────────────────────────────────────────────────────────────────────────────
try:
    import ProPresenter7_Proto.generated.presentation_pb2 as rv_presentation
    import ProPresenter7_Proto.generated.cue_pb2         as rv_cue
    import ProPresenter7_Proto.generated.action_pb2      as rv_action
    import ProPresenter7_Proto.generated.presentationSlide_pb2 as rv_pslide
    import ProPresenter7_Proto.generated.slide_pb2       as rv_slide
    import ProPresenter7_Proto.generated.graphicsData_pb2 as rv_graphics
except ImportError as e:
    sys.stderr.write(
        "❌  Could not import ProPresenter7-Proto generated modules.\n"
        "    Ensure you ran `protoc` on all .proto files and added the generated folder to PYTHONPATH.\n"
        f"    ({e})\n"
    )
    raise

# Short aliases
Presentation       = rv_presentation.Presentation
Cue                = rv_cue.Cue
Action             = rv_action.Action
PresentationSlide  = rv_pslide.PresentationSlide
Slide              = rv_slide.Slide
Graphics           = rv_graphics.Graphics

# ──────────────────────────────────────────────────────────────────────────────
#  Resolve the numeric enum for "presentation slide" action
# ──────────────────────────────────────────────────────────────────────────────
def _resolve_presentation_slide_enum() -> int:
    # top‑level enum
    if hasattr(rv_action, "ActionType") and hasattr(rv_action.ActionType, "ACTION_TYPE_PRESENTATION_SLIDE"):
        return rv_action.ActionType.ACTION_TYPE_PRESENTATION_SLIDE  # type: ignore[attr-defined]
    # nested in Action
    if hasattr(rv_action.Action, "ActionType") and hasattr(rv_action.Action.ActionType, "ACTION_TYPE_PRESENTATION_SLIDE"):
        return rv_action.Action.ActionType.ACTION_TYPE_PRESENTATION_SLIDE  # type: ignore[attr-defined]
    # lookup by name
    for enum_cls in (getattr(rv_action, "ActionType", None), getattr(rv_action.Action, "ActionType", None)):
        if enum_cls:
            try:
                return enum_cls.Value("ACTION_TYPE_PRESENTATION_SLIDE")  # type: ignore[attr-defined]
            except Exception:
                pass
    # fallback
    return 11

ACTION_TYPE_PRESENTATION_SLIDE = _resolve_presentation_slide_enum()

# Every .pro ends with eight NULs (not part of the protobuf)
FOOTER = b"\x00" * 8

# ──────────────────────────────────────────────────────────────────────────────
#  I/O helpers
# ──────────────────────────────────────────────────────────────────────────────

def read_pro(path: str) -> Presentation:
    """Load a .pro file and return a parsed Presentation."""
    with open(path, "rb") as fh:
        raw = fh.read()
    body = raw[:-8] if raw.endswith(FOOTER) else raw
    pres = Presentation()
    pres.ParseFromString(body)
    return pres


def write_pro(pres: Presentation, path: str) -> None:
    """Serialize Presentation to .pro file (re-appends footer)."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'wb') as fh:
        fh.write(pres.SerializeToString() + FOOTER)

# ──────────────────────────────────────────────────────────────────────────────
#  Demo builder (mirrors C# example)
# ──────────────────────────────────────────────────────────────────────────────

def _new_uuid() -> str:
    return str(uuid.uuid4())


def create_demo_presentation() -> Presentation:
    pres = Presentation()
    # Header
    pres.uuid.string = _new_uuid()
    pres.name = "HelloWorld"
    pres.application_info.application = 1  # Propresenter
    pres.application_info.platform    = 2  # Windows

    # --- Slide 1 ---
    cue1 = pres.cues.add()
    cue1.uuid.string    = _new_uuid()
    cue1.isEnabled     = True
    action1 = cue1.actions.add()
    action1.uuid.string = _new_uuid()
    action1.isEnabled  = True
    action1.type        = ACTION_TYPE_PRESENTATION_SLIDE
    # Label color/text
    action1.label.text  = "Hello Slide1"
    action1.label.color.red   = 0.8
    action1.label.color.green = 0.1
    action1.label.color.blue  = 0.4
    action1.label.color.alpha = 1
    # Slide content
    ps1 = action1.slide.presentation  # type: ignore[attr-defined]
    base1 = ps1.base_slide
    base1.uuid.string = _new_uuid()
    base1.draws_background_color = True
    base1.background_color.red   = 0.05
    base1.background_color.green = 0.6
    base1.background_color.blue  = 0.2
    base1.background_color.alpha = 0.4
    base1.size.width  = 1920
    base1.size.height = 1080
    # Element: full-screen transparent, with centered RTF text
    elem1 = base1.elements.add()
    elem1.element.uuid.string = _new_uuid()
    elem1.element.fill.color.alpha = 0
    elem1.element.name = "Hello Element"
    b1 = elem1.element.bounds
    b1.origin.x  = 0; b1.origin.y  = 0
    b1.size.width  = 1920; b1.size.height = 1080
    elem1.element.opacity = 1
    # elem1.element.text.vertical_alignment = Graphics.Text.VerticalAlignment.VERTICAL_ALIGNMENT_CENTER
    elem1.element.text.rtf_data = ("{\\rtf0\\ansi\\ansicpg1252{\\fonttbl\\f0\\fnil ArialMT;}{\\colortbl\\red255\\green255\\blue255;}{\\*\\expandedcolortbl\\csgenericrgb\\c100000\\c100000\\c100000\\c100000;}{\\*\\listtable}{\\*\\listoverridetable}\\uc1\\paperw34407\\margl0\\margr0\\margt0\\margb0\\pard\\li0\\fi0\\ri0\\qc\\sb0\\sa0\\sl240\\slmult1\\slleading0\\f0\\b0\\i0\\ul0\\strike0\\fs200\\expnd0\\expndtw0\\cf0\\strokewidth0\\strokec0\\nosupersub This is the first line of text\\par\\pard\\li0\\fi0\\ri0\\qc\\sb0\\sa0\\sl240\\slmult1\\slleading0\\f0\\b0\\i0\\ul0\\strike0\\fs200\\expnd0\\expndtw0\\cf0\\strokewidth0\\strokec0\\nosupersub And this is the second line of text}".encode('ascii')
    )
    elem1.element.path.shape.type = Graphics.Path.Shape.Type.TYPE_RECTANGLE

    # --- Slide 2 ---
    cue2 = pres.cues.add()
    cue2.uuid.string    = _new_uuid()
    cue2.isEnabled     = True
    action2 = cue2.actions.add()
    action2.uuid.string = _new_uuid()
    action2.isEnabled  = True
    action2.type        = ACTION_TYPE_PRESENTATION_SLIDE
    action2.label.text  = "Hello Slide2"
    action2.label.color.red   = 0.46
    action2.label.color.green = 0.0
    action2.label.color.blue  = 0.8
    action2.label.color.alpha = 1
    ps2 = action2.slide.presentation  # type: ignore[attr-defined]
    base2 = ps2.base_slide
    base2.uuid.string = _new_uuid()
    base2.draws_background_color = True
    base2.background_color.red   = 1.0
    base2.background_color.green = 1.0
    base2.background_color.blue  = 1.0
    base2.background_color.alpha = 1.0
    base2.size.width  = 1920
    base2.size.height = 1080

    # --- Group + Arrangement ---
    grp = pres.cue_groups.add()
    grp.group.uuid.string = _new_uuid()
    grp.group.name        = "Hello Group"
    grp.group.color.red   = 0.0
    grp.group.color.green = 0.467
    grp.group.color.blue  = 0.8
    grp.group.color.alpha = 1
    grp.cue_identifiers.extend([cue1.uuid, cue2.uuid])

    arr = pres.arrangements.add()
    arr.uuid.string = _new_uuid()
    arr.name         = "Hello Arrangement"
    arr.group_identifiers.extend([grp.group.uuid])
    pres.selected_arrangement.CopyFrom(arr.uuid)

    return pres

# ──────────────────────────────────────────────────────────────────────────────
#  CLI entrypoint
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build or demo ProPresenter .pro files via protobuf")
    parser.add_argument("--template", help="Path to existing .pro to inspect", default=None)
    args = parser.parse_args()

    if args.template:
        try:
            existing = read_pro(args.template)
            print(f"✔️ Loaded template with {len(existing.cues)} cues and {len(existing.cue_groups)} groups")
        except DecodeError as e:
            print(f"❌ Failed to parse {args.template}: {e}")

    demo = create_demo_presentation()
    out = os.path.join("output", "HelloWorld.pro")
    write_pro(demo, out)
    print(f"✅ Wrote demo .pro to {out} — {len(demo.cues)} cues, {len(demo.cue_groups)} groups")
