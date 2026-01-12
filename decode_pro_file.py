"""
Utility to decode and inspect ProPresenter .pro files.
Usage: python decode_pro_file.py <path_to_pro_file>
"""
import sys
from pathlib import Path

# Add protobuf modules to path
REPO_ROOT = Path(__file__).resolve().parent
PROTO_PATH = REPO_ROOT / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
sys.path.insert(0, str(PROTO_PATH))

import presentation_pb2
from google.protobuf import text_format, json_format


def decode_pro_file(file_path: str):
    """Decode a .pro file and display its structure."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ File not found: {path}")
        return
    
    print(f"📄 Decoding: {path.name}")
    print(f"   Path: {path}")
    print(f"   Size: {path.stat().st_size:,} bytes\n")
    
    # Read the file
    with open(path, 'rb') as f:
        data = f.read()
    
    # Parse as Presentation protobuf
    presentation = presentation_pb2.Presentation()
    try:
        presentation.ParseFromString(data)
        print("✅ Successfully parsed as Presentation protobuf\n")
    except Exception as e:
        print(f"❌ Failed to parse: {e}\n")
        return
    
    # Display summary
    print("=" * 80)
    print("PRESENTATION SUMMARY")
    print("=" * 80)
    print(f"Application Info: {presentation.application_info}")
    print(f"Number of Cues: {len(presentation.cues)}")
    print(f"Number of Arrangements: {len(presentation.arrangements)}")
    print(f"Selected Arrangement: {presentation.selected_arrangement}")
    
    # Cue details
    if presentation.cues:
        print(f"\n{'=' * 80}")
        print("CUES")
        print("=" * 80)
        for idx, cue in enumerate(presentation.cues):
            print(f"\nCue {idx}:")
            print(f"  UUID: {cue.uuid.string}")
            print(f"  Name: {cue.name}")
            print(f"  Number of Actions: {len(cue.actions)}")
            
            for action_idx, action in enumerate(cue.actions):
                # Determine action type by checking which field is set
                action_type = "unknown"
                if action.HasField('slide'):
                    action_type = "slide"
                elif action.HasField('clear_group'):
                    action_type = "clear_group"
                elif action.HasField('stage_display'):
                    action_type = "stage_display"
                elif action.HasField('prop'):
                    action_type = "prop"
                
                print(f"    Action {action_idx}: {action_type}")
                
                if action.HasField('slide'):
                    slide = action.slide
                    uuid_str = str(slide.uuid) if hasattr(slide, 'uuid') else "N/A"
                    name_str = slide.name if hasattr(slide, 'name') else "N/A"
                    num_elements = len(slide.base_slide.elements) if hasattr(slide, 'base_slide') else 0
                    print(f"      - UUID: {uuid_str}")
                    print(f"      - Name: {name_str}")
                    print(f"      - Number of Elements: {num_elements}")
    
    # Option: Save as JSON
    json_output = path.with_suffix('.json')
    try:
        json_data = json_format.MessageToJson(presentation, indent=2)
        with open(json_output, 'w', encoding='utf-8') as f:
            f.write(json_data)
        print(f"\n✅ JSON export saved to: {json_output}")
    except Exception as e:
        print(f"\n⚠ Could not export to JSON: {e}")
    
    # Option: Save as text format
    txt_output = path.with_suffix('.txt')
    try:
        text_data = text_format.MessageToString(presentation)
        with open(txt_output, 'w', encoding='utf-8') as f:
            f.write(text_data)
        print(f"✅ Text format saved to: {txt_output}")
    except Exception as e:
        print(f"⚠ Could not export to text: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python decode_pro_file.py <path_to_pro_file>")
        print("\nExample:")
        print("  python decode_pro_file.py packages/slides/templates/blank_template_mac.pro")
        sys.exit(1)
    
    decode_pro_file(sys.argv[1])
