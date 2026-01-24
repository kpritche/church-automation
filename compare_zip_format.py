#!/usr/bin/env python3
"""Compare ZIP format details between ProPresenter-generated and Python-generated bundles."""
import zipfile
from pathlib import Path

PP_BUNDLE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\2026-01-25\weekly_announcements_2026-01-25_mac.probundle")
PY_BUNDLE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")

def analyze_zip(path: Path, label: str):
    print(f"\n{'='*60}")
    print(f"{label}: {path.name}")
    print(f"File size: {path.stat().st_size:,} bytes")
    print(f"{'='*60}")
    
    try:
        with zipfile.ZipFile(path, 'r') as z:
            print(f"Is ZIP64: {z._allowZip64 if hasattr(z, '_allowZip64') else 'N/A'}")
            print(f"\nFiles in archive ({len(z.namelist())}):")
            for info in z.infolist():
                compress_type = {
                    0: 'STORED',
                    8: 'DEFLATED',
                    12: 'BZIP2',
                    14: 'LZMA'
                }.get(info.compress_type, f'UNKNOWN({info.compress_type})')
                print(f"  {info.filename}")
                print(f"    compress_type: {compress_type}")
                print(f"    compress_size: {info.compress_size:,}")
                print(f"    file_size: {info.file_size:,}")
                print(f"    flag_bits: {info.flag_bits}")
                print(f"    create_version: {info.create_version}")
                print(f"    extract_version: {info.extract_version}")
    except Exception as e:
        print(f"Error reading ZIP: {e}")

if PP_BUNDLE.exists():
    analyze_zip(PP_BUNDLE, "ProPresenter Generated")
else:
    print(f"ProPresenter bundle not found: {PP_BUNDLE}")

if PY_BUNDLE.exists():
    analyze_zip(PY_BUNDLE, "Python Generated")
else:
    print(f"Python bundle not found: {PY_BUNDLE}")
