#!/usr/bin/env python3
"""
Unified runner for church automation tasks.

Runs both:
1. Announcements generation (announcements_app)
2. ProPresenter slides generation (slides_app)

Note: Packages must be installed first. Run:
  uv sync --all-extras
"""
from __future__ import annotations

import sys


def run_announcements():
    """Run the announcements generation workflow."""
    print("=" * 60)
    print("STEP 1: Generating Announcements ProBundle")
    print("=" * 60)
    try:
        from announcements_app.main_probundle import main as announcements_main
        announcements_main()
        print("✓ Announcements generation completed successfully\n")
    except Exception as e:
        print(f"✗ Announcements generation failed: {e}\n")
        raise


def run_slides():
    """Run the ProPresenter slides generation workflow."""
    print("=" * 60)
    print("STEP 2: Generating ProPresenter Slides")
    print("=" * 60)
    try:
        from slides_app.make_pro import main as slides_main
        slides_main()
        print("✓ ProPresenter slides generation completed successfully\n")
    except Exception as e:
        print(f"✗ ProPresenter slides generation failed: {e}\n")
        raise


def main():
    """Run all church automation tasks in sequence."""
    print("\n" + "=" * 60)
    print("CHURCH AUTOMATION - UNIFIED RUNNER")
    print("=" * 60 + "\n")
    
    try:
        run_announcements()
        run_slides()
        
        print("=" * 60)
        print("ALL TASKS COMPLETED SUCCESSFULLY")
        print("=" * 60)
    except Exception as e:
        print("=" * 60)
        print(f"WORKFLOW FAILED: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
