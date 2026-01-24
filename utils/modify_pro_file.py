"""
Script to read, modify, and write ProPresenter protobuf files.

This script demonstrates how to:
1. Load a .pro file (ProPresenter protobuf binary)
2. Parse it into a Presentation message
3. Modify specific fields
4. Save the modified version
"""

import sys
from pathlib import Path
from google.protobuf import text_format

# Add the generated protobuf modules to the path
_PROTO_PATH = Path(__file__).resolve().parent / "packages" / "slides" / "ProPresenter7_Proto" / "generated"
if str(_PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(_PROTO_PATH))

# Import the generated protobuf message classes
import presentation_pb2
import presentationSlide_pb2
import cue_pb2
import action_pb2
import rvtimestamp_pb2


def load_pro_file(file_path: Path) -> presentation_pb2.Presentation:
    """
    Load a .pro file and parse it into a Presentation message.
    
    Args:
        file_path: Path to the .pro file
        
    Returns:
        Parsed Presentation message
    """
    print(f"Loading: {file_path}")
    
    with open(file_path, 'rb') as f:
        binary_data = f.read()
    
    presentation = presentation_pb2.Presentation()
    presentation.ParseFromString(binary_data)
    
    print(f"✓ Successfully loaded presentation: {presentation.name}")
    print(f"  UUID: {presentation.uuid.string}")
    print(f"  Number of cues (slides): {len(presentation.cues)}")
    
    return presentation


def modify_presentation(presentation: presentation_pb2.Presentation) -> presentation_pb2.Presentation:
    """
    Modify specific fields in the presentation.
    
    Args:
        presentation: The Presentation message to modify
        
    Returns:
        Modified presentation
    """
    print("\n" + "="*60)
    print("MODIFYING PRESENTATION")
    print("="*60)
    
    # ================================================================
    # TODO: MODIFY FIELDS HERE
    # ================================================================
    
    # Example 1: Change the presentation name
    old_name = presentation.name
    presentation.name = "Modified Announcement Template"
    print(f"✓ Changed name: '{old_name}' → '{presentation.name}'")
    
    # Example 2: Modify the category
    old_category = presentation.category
    presentation.category = "Modified Category"
    print(f"✓ Changed category: '{old_category}' → '{presentation.category}'")
    
    # Example 3: Add notes
    presentation.notes = "This presentation was modified by the Python script."
    print(f"✓ Added notes: {presentation.notes}")
    
    # Example 4: Modify slide text (if there are slides)
    if len(presentation.cues) > 0:
        first_slide = presentation.cues[0]
        
        # Access the slide's actions and elements
        if hasattr(first_slide, 'actions') and len(first_slide.actions) > 0:
            for action in first_slide.actions:
                if action.HasField('slide'):
                    slide = action.slide
                    print(f"\n  Found slide: {slide.name}")
                    print(f"  Number of elements: {len(slide.elements)}")
                    
                    # Example: Modify text in the first text element
                    for element in slide.elements:
                        if element.HasField('text'):
                            old_rtf = element.text.rtf_data[:50]  # First 50 chars
                            # TODO: You can modify RTF text here
                            # element.text.rtf_data = b"new RTF text..."
                            print(f"  Text element found (first 50 chars): {old_rtf}")
                            break
    
    # ================================================================
    # Example 5: Modify UUID (uncomment to use)
    # ================================================================
    # from uuid import uuid4
    # new_uuid = str(uuid4())
    # presentation.uuid.string = new_uuid
    # print(f"✓ Changed UUID to: {new_uuid}")
    
    # ================================================================
    # Example 6: Modify CCLI information (if present)
    # ================================================================
    # if presentation.HasField('ccli'):
    #     presentation.ccli.song_number = 12345
    #     presentation.ccli.song_title = "Modified Song Title"
    #     presentation.ccli.author = "Modified Author"
    #     print(f"✓ Modified CCLI info")
    
    # ================================================================
    # END TODO SECTION
    # ================================================================
    
    return presentation


def save_pro_file(presentation: presentation_pb2.Presentation, output_path: Path):
    """
    Serialize the modified presentation to a .pro file.
    
    Args:
        presentation: The Presentation message to save
        output_path: Path where to save the .pro file
    """
    print("\n" + "="*60)
    print("SAVING MODIFIED PRESENTATION")
    print("="*60)
    
    binary_data = presentation.SerializeToString()
    
    with open(output_path, 'wb') as f:
        f.write(binary_data)
    
    print(f"✓ Saved to: {output_path}")
    print(f"  File size: {len(binary_data):,} bytes")


def main():
    """Main execution function."""
    
    # Define file paths
    repo_root = Path(__file__).resolve().parent
    input_file = repo_root / "packages" / "slides" / "templates" / "announcement_template" / "announcement_template.pro"
    output_file = repo_root / "new_modified.pro"
    
    # Verify input file exists
    if not input_file.exists():
        print(f"✗ Input file not found: {input_file}")
        sys.exit(1)
    
    print("="*60)
    print("PROPRESENTER PROTOBUF MODIFIER")
    print("="*60)
    
    # Step 1: Load the .pro file
    presentation = load_pro_file(input_file)
    
    # Step 2: Modify the presentation
    modified_presentation = modify_presentation(presentation)
    
    # Step 3: Display the modified message in human-readable format
    print("\n" + "="*60)
    print("MODIFIED PRESENTATION (TEXT FORMAT)")
    print("="*60)
    
    # Print a compact version (showing key fields only)
    print(f"\nName: {modified_presentation.name}")
    print(f"UUID: {modified_presentation.uuid.string}")
    print(f"Category: {modified_presentation.category}")
    print(f"Notes: {modified_presentation.notes}")
    print(f"Number of slides: {len(modified_presentation.cues)}")
    
    # Uncomment to see the full text format (can be very long)
    # print("\nFull presentation in text format:")
    # print(text_format.MessageToString(modified_presentation))
    
    # Optional: Print just the first slide in detail
    if len(modified_presentation.cues) > 0:
        print("\nFirst slide (text format):")
        print(text_format.MessageToString(modified_presentation.cues[0]))
    
    # Step 4: Save the modified presentation
    save_pro_file(modified_presentation, output_file)
    
    print("\n" + "="*60)
    print("✓ COMPLETE!")
    print("="*60)
    print(f"\nOriginal: {input_file}")
    print(f"Modified: {output_file}")
    print("\nYou can now import the modified .pro file into ProPresenter.")


if __name__ == "__main__":
    main()
