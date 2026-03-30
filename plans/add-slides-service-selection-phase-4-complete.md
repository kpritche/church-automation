## Phase 4 Complete: Implement Reusable Service Selector Frontend Logic

Successfully refactored JavaScript functions from bulletin-specific to generic, creating reusable service selector logic for both bulletins and slides.

**Files created/changed:**
- [packages/web_ui/static/app.js](packages/web_ui/static/app.js)

**Functions created/changed:**
- `showServiceSelector(jobType)` - Generic function to show selector for any job type
- `renderServiceSelector(services, jobType)` - Generic rendering function for service checkboxes
- `generateSelectedServices()` - Generic function to trigger job for selected services
- `hideServiceSelector()` - Generic function to hide the selector
- **Removed**: `showBulletinServiceSelector()`, `generateSelectedBulletins()`, `hideBulletinServiceSelector()` (replaced by generic versions)

**Tests created/changed:**
- Manual testing checklist provided for both bulletins and slides workflows

**Review Status:** APPROVED

**Key Implementation Details:**

**Generic Function Architecture:**

1. **`showServiceSelector(jobType)`**:
   - Accepts 'bulletins' or 'slides' as parameter
   - Fetches from `/api/future-services` (generic endpoint)
   - Sets `data-job-type` attribute to track active job type
   - Updates title dynamically based on job type
   - Uses `service-selector` ID (generic, not bulletin-specific)

2. **`renderServiceSelector(services, jobType)`**:
   - Renders service checkboxes with `data-job-type` attribute
   - Uses generic `.service-checkbox` class
   - Maintains all existing data attributes
   - Groups services by service name
   - Renders into `#service-selector-list`

3. **`generateSelectedServices()`**:
   - Reads job type from selector's `data-job-type` attribute
   - Validates job type is set
   - Selects all checked `.service-checkbox` elements
   - Builds `selected_plans` array with proper structure
   - POSTs to `/api/jobs` with dynamic job type
   - Starts polling with correct job type
   - Hides selector after triggering

4. **`hideServiceSelector()`**:
   - Hides the selector element
   - Clears error messages
   - Resets `data-job-type` attribute

**API Integration:**
✓ Updated endpoint: `/api/future-services` (from bulletin-specific endpoint)  
✓ Compatible with Phase 2 backend changes  
✓ Supports both bulletins and slides job types

**DOM References:**
✓ All references updated to generic `service-selector`  
✓ No bulletin-specific IDs remaining  
✓ Loading/list/error elements use existing generic IDs

**Logic Flow:**

**Bulletins**: 
Click button → `showServiceSelector('bulletins')` → Fetch services → Set `data-job-type="bulletins"` → Render checkboxes → Select services → `generateSelectedServices()` → POST with `job_type: 'bulletins'`

**Slides**: 
Click button → `showServiceSelector('slides')` → Fetch services → Set `data-job-type="slides"` → Render checkboxes → Select services → `generateSelectedServices()` → POST with `job_type: 'slides'`

**Git Commit Message:**
```
feat: Implement reusable service selector frontend logic

- Create showServiceSelector(jobType) generic function
- Create renderServiceSelector(services, jobType) for checkbox rendering
- Create generateSelectedServices() to handle any job type
- Create hideServiceSelector() generic hide function
- Update API endpoint to /api/future-services
- Add data-job-type tracking for active job type
- Remove old bulletin-specific functions
- Support both bulletins and slides workflows with single codebase
```
