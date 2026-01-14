# AC Rules Workflow Implementation Fix - Testing Guide

## Overview

This fix addresses the issue where AC Rules workflow implementation was only checking if a user had ANY rule for a doctype/action combination, not whether they had permission for a specific document.

## Changes Made

### 1. New Function: `has_ac_permission()`

Located in: `tweaks/tweaks/doctype/ac_rule/ac_rule_utils.py`

This function:
- Takes a specific document, doctype, action, and user
- Generates SQL to check if that document matches the AC Rules filters
- Executes the SQL to verify permission
- Returns whether the user has permission for that specific document

**Key Features:**
- Document-level verification (not just doctype-level)
- SQL injection prevention (validates doctype)
- Proper error handling (checks for empty results)
- Supports both doc object and docname/doctype parameters
- Administrator always has full access
- Handles unmanaged resources properly

### 2. Updated Workflow Integration

Located in: `tweaks/utils/workflow.py`

Updated three functions to use `has_ac_permission`:
1. `check_workflow_transition_permission` - Verifies permission before transition
2. `filter_transitions_by_ac_rules` - Filters available transitions based on doc permission
3. `has_workflow_action_permission_via_ac_rules` - Checks action permission for notifications

## Testing Scenarios

### Scenario 1: Basic Document Permission Check

```python
import frappe
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_ac_permission

# Create or get a test document
doc = frappe.get_doc("Purchase Order", "PO-0001")

# Check if current user can approve it
result = has_ac_permission(
    doc=doc,
    doctype="Purchase Order",
    action="approve"
)

print(f"Can approve: {result.get('access')}")
print(f"Unmanaged: {result.get('unmanaged')}")
```

### Scenario 2: Workflow Transition Filtering

**Setup:**
1. Create an AC Resource for a doctype with workflow (e.g., Purchase Order)
2. Add actions: "approve", "reject"
3. Create a Query Filter for principals (e.g., only managers)
4. Create a Query Filter for resources (e.g., only POs in user's territory)
5. Create an AC Rule linking them together

**Test:**
1. Login as a user who matches the principal filter
2. Open a Purchase Order that matches the resource filter
3. Check available workflow actions - should see "Approve" and "Reject"
4. Open a Purchase Order that does NOT match the resource filter
5. Check available workflow actions - should NOT see "Approve" and "Reject"

### Scenario 3: Workflow Transition Execution

**Setup:** Same as Scenario 2

**Test:**
1. Login as a user who matches the principal filter
2. Try to approve a PO that matches the resource filter - should succeed
3. Try to approve a PO that does NOT match the resource filter - should fail with permission error

### Scenario 4: Amount-Based Approval

**Setup:**
1. Create AC Resource for Purchase Order
2. Create Query Filters:
   - Principal: Users with "Approver" role
   - Resource: `grand_total <= 10000`
3. Create AC Rule: "Approve PO under 10k"

**Test:**
1. Login as user with Approver role
2. Create PO with grand_total = 5000
3. Try to approve - should succeed
4. Create PO with grand_total = 15000
5. Try to approve - should fail

### Scenario 5: Territory-Based Access

**Setup:**
1. Create AC Resource for Sales Order
2. Create Query Filters:
   - Principal: Sales Managers
   - Resource: `territory = (SELECT territory FROM tabUser WHERE name = '{user}')`
3. Create AC Rule

**Test:**
1. Set user's territory to "North"
2. Create Sales Order in "North" territory
3. Try to approve - should succeed
4. Create Sales Order in "South" territory
5. Try to approve - should fail

## Manual Test Script

Run this command in your Frappe environment:

```bash
bench --site [your-site] execute tweaks.test_has_ac_permission.test_has_ac_permission
```

This will run the test script that demonstrates the difference between `has_resource_access` and `has_ac_permission`.

## Verification Checklist

- [ ] Test with managed resource (AC Rules configured)
- [ ] Test with unmanaged resource (no AC Rules)
- [ ] Test with Administrator user
- [ ] Test with user who has total access
- [ ] Test with user who has partial access
- [ ] Test with user who has no access
- [ ] Test workflow transition filtering
- [ ] Test workflow transition execution
- [ ] Test with complex Query Filters (SQL with joins)
- [ ] Verify no SQL injection vulnerabilities
- [ ] Verify proper error messages

## Expected Behavior

### Before the Fix

- Workflow actions would be available if user had ANY rule for that action
- User could see actions in the UI but get permission errors when trying to execute them
- `has_resource_access` would return `True` even if the user couldn't act on the specific document

### After the Fix

- Workflow actions are only available if user has permission for THAT specific document
- UI correctly reflects what actions the user can perform
- `has_ac_permission` returns `True` only if the user can act on the specific document
- Consistent behavior between filtering and execution

## Common Issues and Solutions

### Issue: "Invalid DocType" error

**Cause:** DocType validation to prevent SQL injection
**Solution:** Ensure the doctype parameter is a valid Frappe DocType name

### Issue: Getting permission errors even with Administrator

**Cause:** User not properly set to "Administrator"
**Solution:** Verify `frappe.session.user == "Administrator"`

### Issue: AC Rules not applying

**Cause:** Rules might be disabled, outside date range, or cache not cleared
**Solution:**
1. Check rule is enabled
2. Check valid_from and valid_upto dates
3. Clear cache: `frappe.cache.delete_value("ac_rule_map")`

### Issue: Partial access not working correctly

**Cause:** Query Filter might have syntax errors
**Solution:** Test the Query Filter in the Query Filters report with user impersonation

## Additional Resources

- **AC Rules Expert Skill**: `.github/skills/ac-rules-expert/`
- **Integration Documentation**: `.github/skills/ac-rules-expert/references/integration.md`
- **API Review**: `docs/api-review.yaml`
- **Test Script**: `test_has_ac_permission.py`

## Support

If you encounter issues:
1. Check the Query Filters report for SQL generation
2. Check the AC Permissions report for overall access audit
3. Enable debug mode and check Frappe logs
4. Test with Administrator to rule out AC Rules issues
