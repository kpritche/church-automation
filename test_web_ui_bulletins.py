#!/usr/bin/env python3
"""
Test script to simulate web UI bulletin generation in a background thread.
This helps diagnose why web UI might produce different results than terminal.
"""

import threading
import time
import sys
from pathlib import Path

# Add repo root to path (similar to how web UI might work)
repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

def run_bulletins_in_thread():
    """Simulate how web UI runs bulletins in a background thread"""
    print("=" * 80)
    print("SIMULATING WEB UI THREAD EXECUTION")
    print("=" * 80)
    
    # Import inside thread (like web UI does)
    from bulletins_app.make_bulletins import main as gen_bulletins
    
    print(f"\n✓ Thread started: {threading.current_thread().name}")
    print(f"✓ Calling gen_bulletins() from thread...\n")
    
    try:
        gen_bulletins()
        print(f"\n✓ gen_bulletins() completed successfully")
    except Exception as e:
        print(f"\n✗ gen_bulletins() failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)
    print("THREAD EXECUTION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    print("Starting web UI simulation test...")
    print(f"Working directory: {Path.cwd()}")
    print(f"Python: {sys.executable}")
    print()
    
    # Create and start thread
    thread = threading.Thread(target=run_bulletins_in_thread, name="WebUITestThread")
    thread.start()
    
    # Wait for completion
    thread.join()
    
    print("\nTest complete!")
    
    # Check the generated file
    bulletin_path = (
        repo_root / "packages" / "bulletins" / "output" / 
        "Bulletin-2026-03-29-Celebrate-Service.pdf"
    )
    
    if bulletin_path.exists():
        from PyPDF2 import PdfReader
        pdf = PdfReader(str(bulletin_path))
        print(f"\n✓ Bulletin generated: {bulletin_path}")
        print(f"✓ Page count: {len(pdf.pages)}")
        print(f"✓ File size: {bulletin_path.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print(f"\n✗ Bulletin not found: {bulletin_path}")
