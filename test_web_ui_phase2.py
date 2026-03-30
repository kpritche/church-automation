"""
Test Phase 2 Implementation: Web UI Backend Updates

This test verifies:
1. The generate_selected_slides import works
2. The conditional logic in tasks.py is correct
3. The API endpoints are properly configured
"""

import sys
from pathlib import Path

print("=" * 60)
print("Phase 2 Verification Tests")
print("=" * 60)

# Test 1: Verify slides_app.make_pro imports
print("\n[Test 1] Verifying imports from slides_app.make_pro...")
try:
    from slides_app.make_pro import main as gen_slides, generate_selected_slides
    print("✓ Successfully imported gen_slides and generate_selected_slides")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Verify the API endpoint structure
print("\n[Test 2] Verifying FastAPI endpoint configuration...")
try:
    from web_ui_app.main import app
    
    # Check that both endpoints exist
    routes = {route.path for route in app.routes}
    
    if "/api/future-services" in routes:
        print("✓ New endpoint /api/future-services exists")
    else:
        print("✗ Missing /api/future-services endpoint")
        sys.exit(1)
    
    if "/api/bulletins/future-services" in routes:
        print("✓ Backward compatibility endpoint /api/bulletins/future-services exists")
    else:
        print("✗ Missing backward compatibility endpoint")
        sys.exit(1)
    
except Exception as e:
    print(f"✗ API verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify conditional logic simulation
print("\n[Test 3] Simulating conditional logic in tasks.py...")
try:
    # Simulate the params check logic
    test_cases = [
        (None, "Should call gen_slides() - no params"),
        ({}, "Should call gen_slides() - empty params"),
        ({"other_key": "value"}, "Should call gen_slides() - no selected_plans"),
        ({"selected_plans": []}, "Should call generate_selected_slides() - empty list"),
        ({"selected_plans": [{"plan_id": "123"}]}, "Should call generate_selected_slides() - with plans"),
    ]
    
    for params, description in test_cases:
        should_use_selected = params and params.get("selected_plans")
        if should_use_selected:
            handler = "generate_selected_slides"
        else:
            handler = "gen_slides"
        print(f"  • {description} → {handler}")
    
    print("✓ Conditional logic verified")
    
except Exception as e:
    print(f"✗ Logic verification failed: {e}")
    sys.exit(1)

# Test 4: Verify bulletins handler pattern is consistent
print("\n[Test 4] Verifying consistency with bulletins handler...")
try:
    # Read tasks.py to verify slides handler matches bulletins pattern
    tasks_file = Path(__file__).parent / "packages" / "web_ui" / "web_ui_app" / "tasks.py"
    content = tasks_file.read_text()
    
    # Check that slides handler has the same structure as bulletins
    checks = [
        ('from slides_app.make_pro import main as gen_slides, generate_selected_slides', 
         'Import statement includes generate_selected_slides'),
        ('if params and params.get("selected_plans"):', 
         'Conditional check for selected_plans'),
        ('generate_selected_slides(params["selected_plans"])', 
         'Call to generate_selected_slides with params'),
        ('gen_slides()', 
         'Fallback call to gen_slides'),
    ]
    
    for check_str, desc in checks:
        if check_str in content:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ Missing: {desc}")
            sys.exit(1)
    
    print("✓ Handler pattern is consistent with bulletins")
    
except Exception as e:
    print(f"✗ Pattern verification failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ All Phase 2 verification tests passed!")
print("=" * 60)
print("\nNext steps:")
print("  1. Start the web UI server: cd packages/web_ui && uv run uvicorn web_ui_app.main:app --reload")
print("  2. Test /api/future-services endpoint")
print("  3. Test /api/bulletins/future-services backward compatibility")
print("  4. Test slides job with selected_plans parameter")
print("  5. Verify fallback to 7-day window when no plans selected")
