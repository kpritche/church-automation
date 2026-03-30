## Phase 2 Complete: Update Web UI Backend to Handle Slides Selection and Rename Endpoint

Successfully integrated slides service selection into the web UI backend and renamed the API endpoint to be generic for both bulletins and slides.

**Files created/changed:**
- [packages/web_ui/web_ui_app/main.py](packages/web_ui/web_ui_app/main.py)
- [packages/web_ui/web_ui_app/tasks.py](packages/web_ui/web_ui_app/tasks.py)

**Functions created/changed:**
- `get_future_services()` in main.py - Renamed endpoint from `/api/bulletins/future-services` to `/api/future-services`
- Added backward compatibility alias at `/api/bulletins/future-services`
- `run_job_async()` in tasks.py - Updated slides job handler to support `selected_plans` parameter
- Added conditional logic to use `generate_selected_slides()` when plans are selected

**Tests created/changed:**
- Manual verification tests added as comments in code
- Tested import availability, endpoint registration, and conditional logic

**Review Status:** APPROVED

**Key Implementation Details:**

**API Endpoint Changes:**
- Primary endpoint: `/api/future-services` (generic for both job types)
- Backward compatibility: `/api/bulletins/future-services` (alias to same function)
- Response format unchanged: `{"plans": [...]}`

**Task Runner Changes:**
- Import added: `from slides_app.make_pro import generate_selected_slides`
- Conditional logic in slides handler:
  - If `params.get("selected_plans")` exists → calls `generate_selected_slides(params["selected_plans"])`
  - Otherwise → calls `gen_slides()` for default 7-day window
- Pattern mirrors bulletins handler for consistency
- Debug logging added for execution path tracking

**Backward Compatibility:**
✓ Old API endpoint continues to work  
✓ Default 7-day window behavior preserved  
✓ Existing bulletin functionality unaffected  
✓ No breaking changes to existing consumers

**Git Commit Message:**
```
feat: Add slides service selection to web UI backend

- Rename API endpoint from /api/bulletins/future-services to /api/future-services
- Keep backward compatibility alias for old endpoint
- Update tasks.py slides handler to support selected_plans parameter
- Add conditional logic to use generate_selected_slides() when plans provided
- Maintain 7-day window default when no selection made
- Follow same pattern as bulletins handler for consistency
```
