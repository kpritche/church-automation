#!/usr/bin/env python3
"""Compare bundle file structures."""
import zipfile
from pathlib import Path

CORRECTED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\templates\weekly_announcements_2026-01-25_corrected.proBundle")
GENERATED = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")

print("CORRECTED BUNDLE:")
with zipfile.ZipFile(CORRECTED, 'r') as z:
    for f in sorted(z.namelist()):
        print(f"  {f}")

print("\nGENERATED BUNDLE:")
with zipfile.ZipFile(GENERATED, 'r') as z:
    for f in sorted(z.namelist()):
        print(f"  {f}")
