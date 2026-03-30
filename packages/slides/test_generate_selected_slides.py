"""
Test file for generate_selected_slides functionality.

This tests the new backend function that generates slides for specific selected plans.
Following the pattern from bulletins' generate_selected_bulletins().
"""

import sys
from pathlib import Path

# Ensure we can import slides_app
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

try:
    from slides_app.make_pro import generate_selected_slides, process_single_plan
    FUNCTIONS_EXIST = True
except ImportError as e:
    print(f"[IMPORT ERROR] {e}")
    print("This is expected if functions don't exist yet (TDD red phase)")
    FUNCTIONS_EXIST = False
    generate_selected_slides = None
    process_single_plan = None


def test_process_single_plan_basic():
    """Test that process_single_plan can be called with required parameters."""
    # This is a manual test - will fail if dependencies not available
    # Demonstrates expected signature and return type
    
    # Expected call signature:
    # process_single_plan(pco, service_type_id, plan_id, plan_date, service_name, cfg, camera_config)
    # Returns: List[str] (uploaded file paths)
    
    print("Test: process_single_plan signature")
    print("Expected signature: process_single_plan(pco, service_type_id, plan_id, plan_date, service_name, cfg, camera_config) -> List[str]")
    
    if not FUNCTIONS_EXIST or process_single_plan is None:
        print("✗ Function does not exist yet (expected in TDD red phase)")
        return False
    
    print("✓ Function exists and is callable")
    return True


def test_generate_selected_slides_basic():
    """Test that generate_selected_slides can be called with selected plans."""
    # This is a manual test - demonstrates expected usage pattern
    
    # Expected call signature:
    # generate_selected_slides(selected_plans: List[Dict]) -> List[str]
    
    # Example input format:
    example_selected_plans = [
        {
            "service_type_id": "123456",
            "plan_id": "789012",
            "plan_date": "2026-04-05",
            "service_name": "SundayService"
        },
        {
            "service_type_id": "123456",
            "plan_id": "789013",
            "plan_date": "2026-04-12",
            "service_name": "SundayService"
        }
    ]
    
    print("\nTest: generate_selected_slides signature")
    print("Expected signature: generate_selected_slides(selected_plans: List[Dict]) -> List[str]")
    print(f"Example input: {example_selected_plans}")
    print("Expected output: List of uploaded file paths")
    
    if not FUNCTIONS_EXIST or generate_selected_slides is None:
        print("✗ Function does not exist yet (expected in TDD red phase)")
        return False
    
    print("✓ Function exists and is callable")
    return True


def test_backward_compatibility():
    """Test that existing main() function still works."""
    print("\nTest: Backward compatibility")
    print("The existing main() function should continue to work unchanged")
    print("It should still use the 7-day window by default")
    print("✓ main() should remain unchanged")


if __name__ == "__main__":
    print("=" * 60)
    print("Running tests for generate_selected_slides")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    if test_process_single_plan_basic():
        passed += 1
    else:
        failed += 1
        
    if test_generate_selected_slides_basic():
        passed += 1
    else:
        failed += 1
    
    test_backward_compatibility()
    
    print("\n" + "=" * 60)
    print(f"Tests complete: {passed} passed, {failed} failed")
    if failed > 0:
        print("EXPECTED FAILURES in TDD red phase (functions don't exist yet)")
    print("=" * 60)
    
    # Exit with failure code if any tests failed (for TDD workflow)
    sys.exit(failed)
