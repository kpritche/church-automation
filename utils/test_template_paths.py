"""Quick test of the updated pro_generator with the extracted template."""
import sys
from pathlib import Path

# Add to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / "packages" / "announcements"))

from announcements_app import pro_generator

print("=" * 70)
print("TEMPLATE PATH TEST")
print("=" * 70)

print(f"Template .pro file: {pro_generator.ANNOUNCEMENT_TEMPLATE}")
print(f"  Exists: {pro_generator.ANNOUNCEMENT_TEMPLATE.exists()}")

print(f"\nTemplate media dir: {pro_generator.TEMPLATE_MEDIA_DIR}")
print(f"  Exists: {pro_generator.TEMPLATE_MEDIA_DIR.exists()}")

if pro_generator.TEMPLATE_MEDIA_DIR.exists():
    media_files = list(pro_generator.TEMPLATE_MEDIA_DIR.glob('*.*'))
    print(f"  Media files: {len(media_files)}")
    for f in media_files:
        print(f"    - {f.name}")

print(f"\nBlank template: {pro_generator.BLANK_TEMPLATE}")
print(f"  Exists: {pro_generator.BLANK_TEMPLATE.exists()}")

print("\n" + "=" * 70)
print("Loading template...")
try:
    template = pro_generator.load_template(pro_generator.ANNOUNCEMENT_TEMPLATE)
    print(f"✓ Template loaded successfully")
    print(f"  Name: {template.name}")
    print(f"  Cues: {len(template.cues)}")
except Exception as e:
    print(f"✗ Failed to load: {e}")

print("=" * 70)
