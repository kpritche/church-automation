"""
Test script for probundle generation.

This creates a sample .probundle with test data without requiring Gmail access.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from announcements_app.probundle_generator import create_probundle

# Sample test data
test_announcements = [
    {
        "title": "Sunday School Resumes",
        "body": "Join us this Sunday as we kick off our new Sunday School series! Classes for all ages begin at 9:30 AM. Coffee and refreshments will be served.",
        "link": "https://example.com/sunday-school",
        "button_text": "Learn More",
        "image_url": None,  # No image for this one
    },
    {
        "title": "Community Service Day",
        "body": "Volunteers needed! We're organizing a community cleanup on Saturday, January 18th. Meet at the church at 8:00 AM. Supplies provided. Bring gloves and water.",
        "link": None,  # No link/QR for this one
        "button_text": None,
        "image_url": None,
    },
    {
        "title": "Youth Group Pizza Night",
        "body": "All youth (grades 6-12) are invited to our monthly pizza night this Friday at 6:30 PM. Games, music, and fellowship! Parents welcome too.",
        "link": "https://example.com/youth-group",
        "button_text": "RSVP Here",
        "image_url": None,
    },
]

if __name__ == "__main__":
    output_dir = ROOT / "output" / "test"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_path = output_dir / "test_announcements.probundle"
    
    print("Creating test .probundle with sample data...")
    print(f"Output: {output_path}")
    
    try:
        create_probundle(test_announcements, output_path)
        print(f"\n✓ Success! Test file created.")
        print(f"\nTo test in ProPresenter:")
        print(f"  1. Open ProPresenter")
        print(f"  2. File > Open > {output_path}")
        print(f"  3. Verify the 3 announcement slides appear correctly")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
