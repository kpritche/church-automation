#!/usr/bin/env python3
"""Deep compare ZIP structures."""
import zipfile
import struct
from pathlib import Path

PP_BUNDLE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\templates\weekly_announcements_2026-01-25_corrected.proBundle")
PY_BUNDLE = Path(r"c:\Users\Kory's PC\Documents\GitHub\church\packages\announcements\output\test_announcements.probundle")

def analyze_deep(path: Path, label: str):
    print(f"\n{'='*70}")
    print(f"{label}: {path.name}")
    print(f"{'='*70}")
    
    with zipfile.ZipFile(path, 'r') as z:
        for i, info in enumerate(z.infolist()[:5]):  # First 5 files
            print(f"\n[{i}] {info.filename}")
            print(f"    compress_type: {info.compress_type}")
            print(f"    header_offset: {info.header_offset}")
            print(f"    flag_bits: {info.flag_bits:016b} ({info.flag_bits})")
            print(f"    internal_attr: {info.internal_attr}")
            print(f"    external_attr: {info.external_attr}")
            print(f"    create_system: {info.create_system}")
            print(f"    create_version: {info.create_version}")
            print(f"    extract_version: {info.extract_version}")
            print(f"    CRC: {info.CRC}")
            print(f"    date_time: {info.date_time}")

if PP_BUNDLE.exists():
    analyze_deep(PP_BUNDLE, "ProPresenter")

if PY_BUNDLE.exists():
    analyze_deep(PY_BUNDLE, "Python")
