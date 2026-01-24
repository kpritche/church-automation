#!/usr/bin/env python3
"""Compare ZIP format and check file headers."""
import zipfile
import struct
from pathlib import Path

# ProPresenter-generated bundles
PP_BUNDLE_1 = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\templates\weekly_announcements_2026-01-25_corrected.proBundle")
PP_BUNDLE_2 = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\2026-01-25\weekly_announcements_2026-01-25_mac.proBundle")

# Python-generated bundle
PY_BUNDLE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")

def check_file_header(path: Path, label: str):
    """Check the first few bytes to determine archive type."""
    print(f"\n{'='*60}")
    print(f"{label}: {path.name}")
    print(f"File size: {path.stat().st_size:,} bytes")
    print(f"{'='*60}")
    
    with open(path, 'rb') as f:
        header = f.read(16)
        print(f"First 16 bytes (hex): {header.hex()}")
        print(f"First 4 bytes: {header[:4]}")
        
        # Check magic bytes
        if header[:4] == b'PK\x03\x04':
            print("Format: Standard ZIP (PK header)")
        elif header[:2] == b'\x1f\x8b':
            print("Format: GZIP")
        elif header[:6] == b'7z\xbc\xaf\x27\x1c':
            print("Format: 7z archive")
        elif header[:4] == b'Rar!':
            print("Format: RAR archive")
        else:
            print(f"Format: Unknown (magic: {header[:4]})")
    
    # Try to read as ZIP
    try:
        with zipfile.ZipFile(path, 'r') as z:
            print(f"\nZIP readable: YES")
            print(f"Files in archive: {len(z.namelist())}")
            # Show first file info
            if z.infolist():
                info = z.infolist()[0]
                compress_type = {
                    0: 'STORED',
                    8: 'DEFLATED',
                    12: 'BZIP2',
                    14: 'LZMA'
                }.get(info.compress_type, f'UNKNOWN({info.compress_type})')
                print(f"First file: {info.filename}")
                print(f"  compress_type: {compress_type}")
                print(f"  create_version: {info.create_version}")
                print(f"  extract_version: {info.extract_version}")
    except Exception as e:
        print(f"\nZIP readable: NO - {e}")

for bundle in [PP_BUNDLE_1, PP_BUNDLE_2, PY_BUNDLE]:
    if bundle.exists():
        check_file_header(bundle, bundle.parent.name)
    else:
        print(f"\nNot found: {bundle}")
