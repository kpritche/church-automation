## Phase 3 Complete: Create Reusable Service Selector UI Component

Successfully refactored the HTML to create a single reusable service selector component that both bulletins and slides can use.

**Files created/changed:**
- [packages/web_ui/web_ui_app/templates/index.html](packages/web_ui/web_ui_app/templates/index.html)

**Functions created/changed:**
- N/A (HTML-only changes, JavaScript functions will be implemented in Phase 4)

**Tests created/changed:**
- Manual verification: HTML structure is valid and reusable

**Review Status:** APPROVED

**Key Implementation Details:**

**Slides Card Changes:**
- Added "Select Services" button with 🎯 icon
- Button onclick: `showServiceSelector('slides')`
- Matches bulletin button styling

**Bulletins Card Changes:**
- Updated button from `showBulletinServiceSelector()` to `showServiceSelector('bulletins')`
- Maintains same styling and visual appearance

**Service Selector Section (Refactored):**
- **ID renamed**: `bulletin-service-selector` → `service-selector` (generic)
- **Tracking attribute**: Added `data-job-type=""` to track current job type
- **Dynamic title**: Changed to "Select Services" with `id="service-selector-title"` for future updates
- **Generic close function**: `hideBulletinServiceSelector()` → `hideServiceSelector()`
- **Generic generate function**: `generateSelectedBulletins()` → `generateSelectedServices()`
- **Generic button text**: "Generate Selected Bulletins" → "Generate Selected"
- **Preserved child elements**: All existing structure maintained (`service-selector-loading`, `service-selector-list`, `service-selector-error`)

**Reusability Features:**
✓ Single selector component used by both job types  
✓ Data attribute tracks which job type is active  
✓ Generic function names ready for Phase 4 implementation  
✓ Clean, maintainable HTML structure  
✓ Consistent styling across both cards

**Git Commit Message:**
```
feat: Create reusable service selector UI component

- Refactor bulletin-service-selector to generic service-selector
- Add "Select Services" button to slides card
- Update bulletins card to use generic showServiceSelector() function
- Add data-job-type attribute to track active job type
- Change selector title and buttons to be generic
- Maintain consistent styling across both cards
- Prepare for Phase 4 JavaScript implementation
```
