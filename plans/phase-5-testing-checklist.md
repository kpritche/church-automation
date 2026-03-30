# Phase 5 Manual Testing Checklist

## Test Environment Setup

- [ ] Web UI server is running (`uv run python web_ui`)
- [ ] Browser console is open (F12) to check for JavaScript errors
- [ ] Planning Center credentials are configured

## Bulletins Workflow Testing

### Standard Flow (Select Services)
- [ ] Click "Select Services" button on Bulletins card
- [ ] Verify service selector modal appears with title "Select Services for Bulletins"
- [ ] Verify loading spinner appears while fetching services
- [ ] Verify services load correctly and are grouped by service name
- [ ] Verify dates are formatted correctly (e.g., "Jan 5, 2026")
- [ ] Select 2-3 services from different service types
- [ ] Click "Generate Selected" button
- [ ] Verify modal closes
- [ ] Verify progress indicator appears
- [ ] Verify status badge shows "Queued" then "Running"
- [ ] Verify job completes successfully
- [ ] Verify success message appears
- [ ] Verify recent jobs list updates with new entry

### Validation Testing
- [ ] Click "Select Services" on Bulletins card
- [ ] Do NOT check any checkboxes
- [ ] Click "Generate Selected"
- [ ] **Expected:** Alert appears: "Please select at least one service to generate bulletins."
- [ ] Modal remains open
- [ ] Select some services and verify generation works after alert

### Select All/Deselect All
- [ ] Click "Select Services"
- [ ] Click "Select All" button
- [ ] **Expected:** All checkboxes are checked
- [ ] Click "Deselect All" button
- [ ] **Expected:** All checkboxes are unchecked
- [ ] Manually select 1 service and generate successfully

### Default Behavior (Generate Button)
- [ ] Click main "Generate" button (NOT "Select Services")
- [ ] **Expected:** Job starts immediately with default 7-day window
- [ ] Verify backward compatibility - works as before Phase 4

## Slides Workflow Testing

### Standard Flow (Select Services)
- [ ] Click "Select Services" button on Slides card
- [ ] Verify modal title shows "Select Services for Slides"
- [ ] Verify loading spinner appears
- [ ] Verify services load correctly
- [ ] Select 1-2 services
- [ ] Click "Generate Selected"
- [ ] Verify modal closes
- [ ] Verify job starts and runs
- [ ] Verify "Uploaded to Planning Center" section appears
- [ ] Verify uploaded files list is displayed

### Validation Testing
- [ ] Click "Select Services" on Slides card
- [ ] Leave all checkboxes unchecked
- [ ] Click "Generate Selected"
- [ ] **Expected:** Alert: "Please select at least one service to generate slides."
- [ ] Modal stays open
- [ ] Select services and verify successful generation

### Default Behavior (Generate Button)
- [ ] Click main "Generate" button on Slides card
- [ ] **Expected:** Job starts with default 7-day window
- [ ] Verify slides are generated and uploaded
- [ ] Verify backward compatibility maintained

## Error Handling Testing

### No Future Services Available
**Setup:** Temporarily modify PCO date range or ensure no future services exist
- [ ] Click "Select Services" on any card
- [ ] **Expected:** Error message displays: "No future services found. Please check your Planning Center configuration."
- [ ] Verify loading spinner disappears
- [ ] Verify error message is in red error box
- [ ] Verify no checkboxes appear
- [ ] Click "Cancel" to close modal
- [ ] **Restore:** Ensure future services exist again

### Network Failure Simulation
**Setup:** Turn off network or block API endpoint temporarily
- [ ] Click "Select Services"
- [ ] **Expected:** Error message: "Failed to load services: [error details]. Please try again."
- [ ] Verify user-friendly error message
- [ ] **Restore:** Re-enable network
- [ ] Click "Select Services" again
- [ ] **Expected:** Services load successfully (retry works)

### API Error During Job Submission
**Setup:** This is harder to simulate - may require backend modification
- [ ] Attempt to trigger a job that will fail validation
- [ ] **Expected:** Error message: "Failed to start [bulletins/slides] generation: [error details]"
- [ ] Verify status badge shows "Failed"
- [ ] Verify error appears in red error box
- [ ] Verify button re-enables for retry

### Job Timeout Scenario
**Setup:** Job that runs longer than expected
- [ ] Start a job that may take a while
- [ ] Wait for timeout message
- [ ] **Expected:** "Job is taking longer than expected. Check recent jobs below."
- [ ] Verify job still completes in background
- [ ] Verify recent jobs list shows final status

## User Interface Testing

### Loading States
- [ ] Verify loading spinner appears when fetching services
- [ ] Verify loading disappears when services loaded
- [ ] Verify loading disappears when error occurs
- [ ] Verify progress indicator during job execution
- [ ] Verify all loading states have appropriate styling

### Error Message Display
- [ ] Verify error messages are in red boxes
- [ ] Verify error messages contain actionable information
- [ ] Verify error messages don't contain raw stack traces
- [ ] Verify errors clear when retrying operations

### Modal Behavior
- [ ] Verify modal opens correctly with proper title
- [ ] Verify Cancel button closes modal cleanly
- [ ] Verify Generate Selected triggers job and closes modal
- [ ] Verify modal doesn't remain open after successful job start
- [ ] Verify only one modal can be open at a time

### Browser Console
- [ ] Open browser console (F12)
- [ ] Perform all workflows
- [ ] **Expected:** No JavaScript errors or warnings
- [ ] **Expected:** Only console.error for actual errors
- [ ] **Expected:** Clean, no red errors in console

## Edge Cases

### Concurrent Requests
- [ ] Click "Select Services" on Bulletins
- [ ] Before it loads, click "Select Services" on Slides
- [ ] **Expected:** Only one modal visible - behavior is predictable
- [ ] Verify no race conditions or UI glitches

### Cancel During Loading
- [ ] Click "Select Services"
- [ ] Immediately click "Cancel" before services load
- [ ] **Expected:** Modal closes cleanly
- [ ] No errors in console
- [ ] Can open modal again successfully

### Multiple Service Types
- [ ] Verify services are grouped correctly by service name
- [ ] Verify dates within each group are chronological
- [ ] Select services from multiple groups
- [ ] Verify all selected services are sent to backend

### Date Formatting
- [ ] Verify dates display in readable format (e.g., "Jan 5, 2026")
- [ ] Verify dates are sorted correctly (earliest first)
- [ ] Verify plan titles appear if present

## Announcements Card (Unchanged)

### Verify No Impact
- [ ] Click "Generate" on Announcements card
- [ ] **Expected:** Works exactly as before (no service selection)
- [ ] Verify job starts and completes
- [ ] Verify no regression from Phase 4 changes

## Cross-Browser Testing (If Possible)

- [ ] Test in Chrome/Chromium
- [ ] Test in Firefox
- [ ] Test in Safari (if available)
- [ ] Test in Edge
- [ ] Verify consistent behavior across browsers

## Performance Testing

### Large Number of Services
**Setup:** If many future services exist
- [ ] Open service selector with 10+ services
- [ ] Verify loading is reasonably fast (< 2 seconds)
- [ ] Verify UI remains responsive
- [ ] Verify all services render correctly
- [ ] Select all services and verify job submission works

### Rapid Clicking
- [ ] Rapidly click buttons multiple times
- [ ] **Expected:** UI handles gracefully (debouncing or disabling)
- [ ] No duplicate requests sent
- [ ] No UI corruption

## Final Verification

- [ ] All console.log statements removed (except initialization)
- [ ] All console.error statements provide helpful information
- [ ] All error messages are user-friendly and actionable
- [ ] All loading states work correctly
- [ ] All validation works as expected
- [ ] Backward compatibility maintained (default Generate buttons work)
- [ ] No JavaScript errors in browser console
- [ ] Code is clean and well-structured

## Test Results Summary

**Date Tested:** _________________

**Tester:** _________________

**Total Tests:** 80+

**Pass:** _______

**Fail:** _______

**Notes:**

---

## Issues Found

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| | | | |

---

## Sign-off

- [ ] All critical workflows tested and passing
- [ ] All error handling tested and working
- [ ] No regressions from previous phases
- [ ] UI/UX is polished and user-friendly
- [ ] Code is production-ready

**Approved by:** _________________ **Date:** _________________
