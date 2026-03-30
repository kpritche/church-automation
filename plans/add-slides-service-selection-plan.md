## Plan: Add Service Selection to Slides Generation in Web UI

Enable users to select specific future services for slides generation through the web UI, mirroring the bulletin service selection functionality. The implementation will refactor the existing endpoint to be generic, create a reusable service selector component, and follow the same architectural pattern as bulletins.

**Phases: 5**

### Phase 1: Create `generate_selected_slides()` Backend Function
**Objective:** Extract and refactor slides generation logic to support a list of selected plans, similar to `generate_selected_bulletins()`.

**Files/Functions to Modify/Create:**
- [packages/slides/slides_app/make_pro.py](packages/slides/slides_app/make_pro.py)
  - Create new function: `generate_selected_slides(selected_plans: List[Dict]) -> List[str]`
  - Extract reusable logic from `main()` for processing individual plans
  - Create helper: `process_single_plan(pco, service_type_id, plan_id, plan_date, service_name, cfg, camera_config) -> List[str]`

**Tests to Write:**
- `test_generate_selected_slides_single_plan()` - Verify single plan processing
- `test_generate_selected_slides_multiple_plans()` - Verify batch processing across service types
- `test_generate_selected_slides_empty_list()` - Verify graceful handling of empty input
- `test_generate_selected_slides_invalid_plan()` - Verify error handling for missing plan data

**Steps:**
1. Write failing tests for `generate_selected_slides()` that mock PCO responses
2. Extract the per-plan processing logic from `main()` into `process_single_plan()` helper function
3. Create `generate_selected_slides()` that accepts `List[Dict]` with keys: `service_type_id`, `plan_id`, `plan_date`, `service_name`
4. Load config, initialize PCO client, iterate selected plans and process each
5. Return list of uploaded file paths
6. Run tests to ensure they pass
7. Verify `main()` still works for backward compatibility (7-day window default)

---

### Phase 2: Update Web UI Backend to Handle Slides Selection and Rename Endpoint
**Objective:** Modify task runner for slides selection support and rename the API endpoint to be generic for both bulletins and slides.

**Files/Functions to Modify/Create:**
- [packages/web_ui/web_ui_app/main.py](packages/web_ui/web_ui_app/main.py)
  - Rename endpoint: `/api/bulletins/future-services` → `/api/future-services`
  - Keep old endpoint as alias for backward compatibility
- [packages/web_ui/web_ui_app/tasks.py](packages/web_ui/web_ui_app/tasks.py)
  - Modify `run_job_async()` slides branch
  - Import `generate_selected_slides` from `slides_app.make_pro`
  - Add conditional logic for `selected_plans` parameter

**Tests to Write:**
- `test_run_job_async_slides_with_selection()` - Verify selected_plans triggers new function
- `test_run_job_async_slides_default()` - Verify backward compatibility (7-day window)
- `test_slides_job_error_handling()` - Verify errors are caught and logged
- `test_future_services_endpoint()` - Verify renamed endpoint works

**Steps:**
1. Write failing tests for the slides job branching logic
2. In main.py, create new `/api/future-services` endpoint
3. Keep `/api/bulletins/future-services` as an alias that calls the same function
4. Import `generate_selected_slides` in tasks.py
5. Add conditional check in slides job handler: if `params.get("selected_plans")`, call `generate_selected_slides()`, else call `main()`
6. Update job status tracking to include uploaded file count
7. Run tests to confirm they pass

---

### Phase 3: Create Reusable Service Selector UI Component
**Objective:** Refactor HTML to create a single reusable service selector that both bulletins and slides can use.

**Files/Functions to Modify/Create:**
- [packages/web_ui/web_ui_app/templates/index.html](packages/web_ui/web_ui_app/templates/index.html)
  - Add "Select Services" button to slides card
  - Refactor bulletin selector section into a generic reusable component
  - Add data attributes to identify which job type is using the selector
  - Ensure IDs and classes support both use cases

**Tests to Write:**
- Manual test: Verify both bulletin and slides selectors display correctly
- Manual test: Verify selector starts hidden and shows on button click
- Manual test: Verify selector can be used by both job types

**Steps:**
1. Identify the current bulletin selector HTML structure
2. Refactor into a generic `service-selector-section` that accepts job type context
3. Add "Select Services" button to slides card with appropriate onclick handler
4. Add data attributes like `data-job-type` to track which feature is using the selector
5. Update CSS classes to be job-agnostic
6. Verify HTML validates and displays correctly
7. Test manually that both bulletin and slides buttons work

---

### Phase 4: Implement Reusable Service Selector Frontend Logic
**Objective:** Create generic JavaScript functions for the service selector that both bulletins and slides can use.

**Files/Functions to Modify/Create:**
- [packages/web_ui/static/app.js](packages/web_ui/static/app.js)
  - Refactor `showBulletinServiceSelector()` into generic `showServiceSelector(jobType)`
  - Refactor `generateSelectedBulletins()` into generic `generateSelectedServices(jobType)`
  - Create `renderServiceSelector(services, jobType)` to handle both cases
  - Update bulletin code to use new generic functions
  - Add slides-specific wrappers that call generic functions

**Tests to Write:**
- Manual test: Verify slides selector fetches and displays services
- Manual test: Verify slides selector allows cross-service-type selection
- Manual test: Verify error when no plans selected
- Manual test: Verify job trigger with correct payload
- Manual test: Verify bulletin functionality still works after refactor

**Steps:**
1. Create `showServiceSelector(jobType)` that fetches from `/api/future-services`
2. Pass jobType to selector display and rendering functions
3. Create `renderServiceSelector(services, jobType)` that groups by service_name and generates checkboxes
4. Use class `.service-checkbox` with data attribute `data-job-type="${jobType}"`
5. Create `generateSelectedServices(jobType)` that reads checked boxes, validates selection, and POSTs to `/api/jobs`
6. Update existing bulletin button handlers to call generic functions with `jobType='bulletins'`
7. Add slides button handlers that call generic functions with `jobType='slides'`
8. Test both bulletin and slides workflows manually

---

### Phase 5: Integration Testing and Error Handling
**Objective:** End-to-end manual testing of the full workflow, error handling improvements, and user feedback.

**Files/Functions to Modify/Create:**
- [packages/web_ui/static/app.js](packages/web_ui/static/app.js)
  - Add error handling for API failures
  - Add user feedback messages for validation errors
  - Add loading states during service fetch
- [packages/web_ui/web_ui_app/templates/index.html](packages/web_ui/web_ui_app/templates/index.html)
  - Ensure error display elements exist
  - Add user-friendly messages

**Tests to Write:**
- Manual test: Full workflow from clicking "Select Services" to slides generation
- Manual test: API error handling (disconnect network and verify graceful failure)
- Manual test: Empty service list handling
- Manual test: No selection validation
- Manual test: Concurrent bulletin and slides requests
- Manual test: Verify 7-day window still works when not using selector

**Steps:**
1. Add error handling in `showServiceSelector()` for fetch failures
2. Display error messages in the selector error container
3. Add validation in `generateSelectedServices()` to check for empty selection
4. Show user-friendly alert if no services selected
5. Add loading spinners during API calls
6. Test full workflow manually with real PCO connection
7. Test error scenarios (network failures, empty results, invalid data)
8. Verify backward compatibility: default behavior still uses 7-day window
9. Document any limitations or known issues
10. Clean up any console warnings or errors

---

**Implementation Notes:**
- Endpoint renamed: `/api/bulletins/future-services` → `/api/future-services` (with backward compatibility alias)
- Single reusable service selector component for both bulletins and slides
- Default 7-day window preserved for backward compatibility
- Cross-service-type selection supported
- Manual testing approach (no JavaScript test infrastructure)
