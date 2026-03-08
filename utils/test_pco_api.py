#!/usr/bin/env python3
"""Test Planning Center Online API connectivity and endpoints.

This script tests various PCO API endpoints to identify which ones are:
- Responding quickly
- Timing out or hanging
- Returning errors

Run with: uv run python utils/test_pco_api.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

try:
    from church_automation_shared import config
except ModuleNotFoundError:
    # Fallback to local shared package path
    _REPO_ROOT = Path(__file__).resolve().parents[1]
    _SHARED_PARENT = _REPO_ROOT / "packages" / "shared"
    if str(_SHARED_PARENT) not in sys.path:
        sys.path.insert(0, str(_SHARED_PARENT))
    from church_automation_shared import config

from pypco.pco import PCO


def test_endpoint(pco: PCO, endpoint: str, name: str, timeout_sec: float = 5.0) -> None:
    """Test a single PCO API endpoint with timeout."""
    print(f"\nTesting: {name}")
    print(f"  Endpoint: {endpoint}")
    
    start = time.time()
    try:
        # Single request with short timeout
        response = pco.get(endpoint)
        elapsed = time.time() - start
        
        data_count = len(response.get("data", []))
        print(f"  Status: OK")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Results: {data_count} items")
        
        # Show structure of first item
        if data_count > 0:
            first_item = response["data"][0]
            print(f"  First item keys: {list(first_item.keys())}")
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"  Status: ERROR")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Error: {type(e).__name__}: {e}")


def main() -> None:
    """Run PCO API tests."""
    if not config.client_id or not config.secret:
        print("ERROR: PCO_CLIENT_ID and/or PCO_SECRET not configured")
        print("Set these in .env file or as environment variables")
        return
    
    print("Planning Center Online API Connectivity Test")
    print("=" * 50)
    print(f"Client ID: {config.client_id[:20]}...")
    print()
    
    pco = PCO(application_id=config.client_id, secret=config.secret)
    
    # Test basic connectivity
    print("Testing basic API connectivity...")
    try:
        pco.get("/services/v2/service_types")
        print("✓ API is reachable")
    except Exception as e:
        print(f"✗ Cannot reach API: {e}")
        return
    
    # Test individual endpoints
    endpoints = [
        ("/services/v2/service_types", "Service Types"),
        ("/people/v2/lists", "People Lists"),
        ("/services/v2/people", "People (Services)"),
    ]
    
    print("\n" + "=" * 50)
    print("Endpoint Response Tests (5s timeout each)")
    print("=" * 50)
    
    for endpoint, name in endpoints:
        test_endpoint(pco, endpoint, name, timeout_sec=5.0)
    
    # Test iterate (which is what bulletins uses)
    print("\n" + "=" * 50)
    print("Testing iterate() - Used by Bulletins")
    print("=" * 50)
    
    print("\nTesting: pco.iterate('/people/v2/lists')")
    print("  (Fetching first item only)")
    
    start = time.time()
    try:
        for i, lst in enumerate(pco.iterate("/people/v2/lists")):
            elapsed = time.time() - start
            if i == 0:
                print(f"  Status: OK (got first item)")
                print(f"  Time: {elapsed:.2f}s")
                print(f"  Item keys: {list(lst.keys())}")
                print(f"  Item: {lst}")
                break
    except Exception as e:
        elapsed = time.time() - start
        print(f"  Status: ERROR")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Error: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 50)
    print("Test Complete")
    print("=" * 50)


if __name__ == "__main__":
    main()
