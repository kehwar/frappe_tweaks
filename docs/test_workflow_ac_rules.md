# Workflow Action AC Rules Integration Tests

This document describes the test suite for the Workflow Action AC Rules integration in Frappe Tweaks.

## Overview

The test suite validates the integration between Frappe's workflow system and the Access Control (AC) Rules permission system. This integration allows fine-grained control over which users can perform specific workflow actions on documents.

## Test File Location

`tweaks/tests/test_workflow_ac_rules.py`

## Components Tested

### 1. `check_workflow_transition_permission`
Hook handler for `before_transition` event that validates AC Rules permission before allowing a workflow transition.

**Tests:**
- `test_check_workflow_transition_permission_with_permission` - Verifies users with AC permission can perform transitions
- `test_check_workflow_transition_permission_without_permission` - Verifies users without AC permission are blocked with PermissionError

### 2. `filter_transitions_by_ac_rules`
Hook handler for `filter_workflow_transitions` that filters out transitions the user doesn't have permission for.

**Tests:**
- `test_filter_transitions_by_ac_rules_with_permission` - Verifies allowed transitions are included
- `test_filter_transitions_by_ac_rules_without_permission` - Verifies disallowed transitions are excluded

### 3. `has_workflow_action_permission_via_ac_rules`
Direct permission check function for workflow actions.

**Tests:**
- `test_has_workflow_action_permission_via_ac_rules_with_permission` - Returns True for allowed actions
- `test_has_workflow_action_permission_via_ac_rules_without_permission` - Returns False for disallowed actions
- `test_transition_without_action` - Edge case: transitions without action are allowed by default

### 4. `get_workflow_action_permission_query_conditions`
Generates SQL WHERE clause for filtering Workflow Action documents based on AC Rules.

**Tests:**
- `test_get_workflow_action_permission_query_conditions_administrator` - Administrator gets no restrictions (empty conditions)
- `test_get_workflow_action_permission_query_conditions_with_rules` - Query conditions are generated for users with AC Rules

### 5. Edge Cases and Integration Tests

**Tests:**
- `test_forbid_rule_blocks_permission` - Forbid rules take precedence over Permit rules
- `test_unmanaged_resource_allows_all` - Resources without AC Rules allow all users (falls through to standard Frappe permissions)

## Test Data Structure

The test suite creates the following test data:

### Users
- `test_workflow_user1@example.com` - Test User 1
- `test_workflow_user2@example.com` - Test User 2

### Roles
- `Workflow Test Role 1` - Assigned to Test User 1
- `Workflow Test Role 2` - Assigned to Test User 2

### DocType
- `Test Workflow DocType` - Custom DocType with workflow enabled

### Workflow
- `Test Workflow DocType Workflow` with states:
  - Draft (initial)
  - Approved (via "Approve" action)
  - Rejected (via "Reject" action)

### AC Rules Components
- **AC Actions**: `approve`, `reject`
- **AC Resource**: For `Test Workflow DocType`
- **Query Filters**: User-specific and all-documents filters
- **AC Rules**: Dynamic Permit/Forbid rules created per test

## Running the Tests

### In Frappe Bench Environment

```bash
# Run all tests in the file
bench --site [site-name] run-tests --module tweaks.tests.test_workflow_ac_rules

# Run a specific test
bench --site [site-name] run-tests --module tweaks.tests.test_workflow_ac_rules --test TestWorkflowACRules.test_check_workflow_transition_permission_with_permission

# Run tests in parallel (faster)
bench --site [site-name] run-parallel-tests --module tweaks.tests.test_workflow_ac_rules
```

### In CI/CD

The tests will automatically run as part of the CI workflow when changes are pushed. See `.github/workflows/ci.yml` for configuration.

## Test Coverage

The test suite covers:

1. ✅ Permission validation on workflow transitions
2. ✅ Filtering of available transitions based on AC Rules
3. ✅ Direct permission checks for workflow actions
4. ✅ SQL query condition generation for Workflow Actions
5. ✅ Administrator bypass (full access)
6. ✅ Permit rules allowing access
7. ✅ Forbid rules blocking access
8. ✅ Unmanaged resources (no AC Rules) falling through to standard permissions
9. ✅ Edge cases (transitions without action)
10. ✅ Cache management
11. ✅ Multiple user scenarios

## Dependencies

The tests depend on:
- Frappe framework test utilities (`frappe.tests.utils.FrappeTestCase`)
- AC Rules system (AC Action, AC Resource, AC Rule, Query Filter)
- Workflow system (Workflow, Workflow State, Workflow Transition, Workflow Action)

## Cleanup

The test suite includes comprehensive cleanup in:
- `tearDownClass()` - Removes all test data after all tests complete
- Individual test methods - Clean up documents created within each test

This ensures tests don't interfere with each other and don't leave orphaned data.

## Notes

- Tests use `frappe.set_user()` to switch user context and test permissions
- AC Rule cache is cleared before each test to ensure consistent state
- All test data is prefixed with "Test Workflow" for easy identification
- Tests use `ignore_permissions=True` when creating test data to bypass standard Frappe permissions
