#!/usr/bin/env python3
"""
Complete example: Generate ProPresenter .probundle from announcement data.

This script demonstrates the full workflow:
1. Compiling protobuf definitions
2. Loading a template (from JSON or binary .pro)
3. Creating slides with the factory pattern
4. Generating UUIDs for all elements
5. Creating the final .probundle file

Author: Senior Python Developer
Date: 2026-01-11
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add paths for imports
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "packages" / "shared"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "announcements"))

from announcements_app.probundle_generator import create_probundle


def main():
    """Generate a .probundle file from example announcement data."""
    
    print("=" * 80)
    print("ProPresenter .probundle Generator - Complete Example")
    print("=" * 80)
    
    # Step 1: Define announcement data (normally from Gmail)
    print("\n📋 Step 1: Preparing announcement data...")
    announcements = [
        {
            "title": "Welcome to Our Church!",
            "body": "Join us this Sunday for a special service. We're excited to worship together "
                   "and celebrate God's love. All are welcome!",
            "link": "https://example.com/welcome",
            "button_text": "Learn More",
            "image_url": "https://picsum.photos/800/600"  # Example image
        },
        {
            "title": "Youth Group Meeting",
            "body": "Our youth group meets every Wednesday at 6 PM. This week we'll be discussing "
                   "faith in action and how we can serve our community. Pizza provided!",
            "link": "https://example.com/youth",
            "button_text": "Sign Up Here",
            "image_url": "https://picsum.photos/800/600?random=1"
        },
        {
            "title": "Community Outreach",
            "body": "Join us for our monthly community service day! We'll be serving meals at the "
                   "local shelter and organizing donations. Every hand helps make a difference.",
            "link": "https://example.com/outreach",
            "button_text": "Volunteer Now",
            # No image for this one
        }
    ]
    
    print(f"   ✓ Loaded {len(announcements)} announcements")
    
    # Step 2: Set output path
    output_dir = REPO_ROOT / "packages" / "announcements" / "output" / "example"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "example_announcements.probundle"
    
    print(f"\n📁 Step 2: Output path set to:")
    print(f"   {output_path}")
    
    # Step 3: Generate the .probundle file
    print(f"\n🔧 Step 3: Generating .probundle file...")
    print("   This includes:")
    print("   - Creating slides from template")
    print("   - Regenerating all UUIDs (critical!)")
    print("   - Generating QR codes")
    print("   - Downloading images")
    print("   - Packaging into .probundle format")
    print()
    
    try:
        create_probundle(announcements, output_path)
        
        print(f"\n{'=' * 80}")
        print("✅ SUCCESS!")
        print(f"{'=' * 80}")
        print(f"\nGenerated file: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"\nYou can now import this .probundle into ProPresenter.")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n{'=' * 80}")
        print("❌ ERROR!")
        print(f"{'=' * 80}")
        print(f"\n{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
