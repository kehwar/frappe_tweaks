# Workflow Action AC Rules Integration Tests

This document describes the test suite for the Workflow Action AC Rules integration in Frappe Tweaks.

## Overview

The test suite validates the integration between Frappe's workflow system and the Access Control (AC) Rules permission system. This integration allows fine-grained control over which users can perform specific workflow actions on documents.

## Test File Location

`tweaks/tests/test_workflow_ac_rules.py`

## Current Test Coverage

**Note:** The tests are currently minimal to avoid complex DocType creation in the CI environment. Full integration tests with custom DocTypes, workflows, and AC Rules should be run manually in a development environment.

### 1. Import Verification
- `test_imports` - Verifies that all workflow AC rules functions can be imported correctly

### 2. Basic Functionality Tests
- `test_get_workflow_action_permission_query_conditions_administrator` - Verifies Administrator gets no restrictions (empty conditions)
- `test_has_workflow_action_permission_no_action` - Verifies transitions without action are allowed by default

## Components Tested

The test suite validates the following workflow AC rules integration functions:

1. **`check_workflow_transition_permission`** - Hook handler for `before_transition` event that validates AC Rules permission before allowing a workflow transition
2. **`filter_transitions_by_ac_rules`** - Hook handler for `filter_workflow_transitions` that filters out transitions the user doesn't have permission for
3. **`has_workflow_action_permission_via_ac_rules`** - Direct permission check function for workflow actions
4. **`get_workflow_action_permission_query_conditions`** - Generates SQL WHERE clause for filtering Workflow Action documents based on AC Rules

## Running the Tests

### In Frappe Bench Environment

```bash
# Run all tests in the file
bench --site [site-name] run-tests --module tweaks.tests.test_workflow_ac_rules

# Run a specific test
bench --site [site-name] run-tests --module tweaks.tests.test_workflow_ac_rules --test TestWorkflowACRules.test_imports

# Run tests in parallel (faster)
bench --site [site-name] run-parallel-tests --module tweaks.tests.test_workflow_ac_rules
```

### In CI/CD

The tests will automatically run as part of the CI workflow when changes are pushed. See `.github/workflows/ci.yml` for configuration.

## Manual Integration Testing

For comprehensive testing of the workflow action AC rules integration, follow these steps in a development environment:

### Test Setup

1. **Create Test Users**
   - Create users with different roles
   - Example: test_user_1@example.com, test_user_2@example.com

2. **Create Test Roles**
   - Create custom roles for testing
   - Example: "Workflow Test Role 1", "Workflow Test Role 2"

3. **Create a DocType with Workflow**
   - Create a custom DocType (e.g., "Test Workflow Document")
   - Add a workflow with multiple states and transitions
   - Configure workflow actions like "Approve", "Reject"

4. **Create AC Actions**
   - Navigate to AC Action list
   - Create actions matching your workflow actions: "approve", "reject"

5. **Create AC Resource**
   - Navigate to AC Resource list
   - Create a resource for your test DocType
   - Select "All" for managed actions

6. **Create AC Rules**
   - Create Permit rules for specific users/roles and actions
   - Create Forbid rules to test blocking behavior
   - Test with Query Filters to limit access to specific documents

### Test Scenarios

**Permission validation on transitions:**
- Users with AC Rules permission can perform transitions
- Users without permission are blocked with `PermissionError`

**Transition filtering:**
- Allowed transitions appear in available actions
- Disallowed transitions are filtered out from the list

**Direct permission checks:**
- `has_workflow_action_permission_via_ac_rules` returns correct boolean for permission status
- Handles transitions without action (edge case)

**SQL query generation:**
- Administrator gets empty conditions (full access)
- Regular users get appropriate AC Rules WHERE clauses

**Rule precedence and special cases:**
- Forbid rules override Permit rules
- Unmanaged resources (no AC Rules) allow all users
- Cache management between rule changes

## Limitations

The current automated test suite is minimal because:
- Creating custom DocTypes dynamically in tests is complex and unreliable in CI
- Frappe's test framework expects DocTypes to exist before tests run
- Full integration tests require database migrations and complex setup

## Future Improvements

To enhance test coverage:
1. Create test fixture DocTypes with JSON definitions
2. Add test fixtures for workflows and AC Rules
3. Implement more comprehensive integration tests
4. Add performance tests for AC Rules query generation

## Dependencies

The tests depend on:
- Frappe framework test utilities (`frappe.tests.utils.FrappeTestCase`)
- Workflow utilities from `tweaks.utils.workflow`
- AC Rules system (implicitly tested through the workflow integration)
