# Monkeypatch Migration Guide

This document lists all monkeypatches in the `frappe_tweaks` repository and provides guidance on how to migrate them to a forked version of Frappe/ERPNext.

## Overview

The `frappe_tweaks` app currently uses several monkeypatches to extend and modify core Frappe/ERPNext functionality. These patches are applied when the app is initialized (see `tweaks/__init__.py` and `tweaks/custom/patches.py`).

Since you're now maintaining a fork of Frappe/ERPNext, these monkeypatches can be migrated directly into the core framework, making them more maintainable and reducing the risk of conflicts with future Frappe updates.

---

## Monkeypatches Inventory

### 1. Document.run_method

**Location:** `tweaks/custom/doctype/document.py`

**What it patches:**
- `frappe.model.document.Document.run_method`
- Adds two new methods: `Document.get_method_args()` and `Document.get_method_kwargs()`

**Purpose:**
- Extends the standard `run_method` to execute Server Scripts for document events
- Adds support for Event Scripts (deprecated)
- Stores method arguments and kwargs in flags for later retrieval

**Current Implementation:**
```python
def apply_document_patches():
    Document.run_method = run_method
    Document.get_method_args = get_method_args
    Document.get_method_kwargs = get_method_kwargs
```

**Migration Strategy:**

**Option 1: Direct Integration (Recommended)**
- Modify `frappe/model/document.py` directly
- Add the enhanced `run_method` implementation to the `Document` class
- Add `get_method_args` and `get_method_kwargs` as proper class methods
- Add a new hook point: `doc_event_hooks` or `before_doc_event` / `after_doc_event`

**Option 2: Hook-based Approach**
- Create new hooks in `frappe/model/document.py`:
  - `doc_event_before_hook` - called before executing doc event
  - `doc_event_after_hook` - called after executing doc event
- Move the Server Script and Event Script execution logic to these hooks

**Files to Modify in Frappe:**
- `frappe/model/document.py` - Add enhanced `run_method` or new hooks

**Benefits:**
- Server Scripts become a native feature of Frappe
- Better performance (no monkeypatch overhead)
- More maintainable code

---

### 2. Server Script Enhancements

**Location:** `tweaks/custom/doctype/server_script_customization.py`

**What it patches:**
- `frappe.core.doctype.server_script.server_script_utils.get_server_script_map`
- `frappe.handler.get_server_script_map`
- `frappe.model.db_query.get_server_script_map`
- `frappe.core.doctype.server_script.server_script_utils.run_server_script_for_doc_event`
- `frappe.model.document.run_server_script_for_doc_event`

**Purpose:**
- Adds support for script priorities
- Adds new script types: "Permission Policy" and "Permission Query"
- Enhances Server Script with additional fields (title, reference_script, priority, description)
- Modifies the event map to include more events

**Current Implementation:**
```python
def apply_server_script_patches():
    # get_server_script_map
    server_script_utils.get_server_script_map = get_server_script_map
    handler.get_server_script_map = get_server_script_map
    db_query.get_server_script_map = get_server_script_map
    
    # run_server_script_for_doc_event
    server_script_utils.run_server_script_for_doc_event = run_server_script_for_doc_event
    document.run_server_script_for_doc_event = run_server_script_for_doc_event
```

**Enhanced EVENT_MAP:**
```python
EVENT_MAP = {
    "before_insert": "Before Insert",
    "after_insert": "After Insert",
    "before_validate": "Before Validate",
    "validate": "Before Save",
    "on_update": "After Save",
    "before_rename": "Before Rename",
    "after_rename": "After Rename",
    "before_submit": "Before Submit",
    "on_submit": "After Submit",
    "before_cancel": "Before Cancel",
    "on_cancel": "After Cancel",
    "on_trash": "Before Delete",
    "after_delete": "After Delete",
    "before_update_after_submit": "Before Save (Submitted Document)",
    "on_update_after_submit": "After Save (Submitted Document)",
    "before_print": "Before Print",
    "on_payment_authorized": "On Payment Authorization",
    "before_transition": "Before Transition",
    "after_transition": "After Transition",
    "before_change": "Before Change",
    "on_change": "After Change",
}
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/core/doctype/server_script/server_script_utils.py`:
   - Replace `get_server_script_map` with the enhanced version
   - Replace `run_server_script_for_doc_event` with the enhanced version
   - Update `EVENT_MAP` with additional events

2. Modify `frappe/core/doctype/server_script/server_script.json`:
   - Add custom fields: `title`, `reference_script`, `priority`, `description`
   - Update script_type options to include "Permission Policy" and "Permission Query"

3. Update imports in:
   - `frappe/handler.py`
   - `frappe/model/db_query.py`
   - `frappe/model/document.py`

**Files to Modify in Frappe:**
- `frappe/core/doctype/server_script/server_script.json`
- `frappe/core/doctype/server_script/server_script.py`
- `frappe/core/doctype/server_script/server_script_utils.py`
- `frappe/handler.py`
- `frappe/model/db_query.py`
- `frappe/model/document.py`

**Custom Fields to Add:**
- `title` (Data, required)
- `reference_script` (Link to Server Script)
- `priority` (Int, default: 100)
- `description` (Text Editor)

---

### 3. Workflow Enhancements

**Location:** `tweaks/custom/doctype/workflow.py`

**What it patches:**
- `frappe.model.workflow.get_transitions`
- `frappe.model.workflow.apply_workflow`

**Purpose:**
- Adds auto-apply functionality for workflow transitions
- Adds custom transition methods: `before_transition`, `after_transition`
- Adds auto workflow transition support

**Current Implementation:**
```python
def apply_workflow_patches():
    workflow.get_transitions = get_transitions
    workflow.apply_workflow = apply_workflow
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/model/workflow.py`:
   - Replace `get_transitions` and `apply_workflow` with enhanced versions
   - Add `apply_workflow_transition` and `apply_auto_workflow_transition` functions

2. Add custom field to Workflow Transition doctype:
   - `auto_apply` (Check field)

3. Add doc event hook for auto-workflow:
   - Hook into `on_change` event to call `apply_auto_workflow_transition`

**Files to Modify in Frappe:**
- `frappe/model/workflow.py`
- `frappe/workflow/doctype/workflow_transition/workflow_transition.json`

**Custom Fields to Add:**
- Workflow Transition: `auto_apply` (Check)

**New Document Methods:**
- `before_transition(transition)` - called before applying transition
- `after_transition(transition)` - called after applying transition

---

### 4. Authentication Enhancement

**Location:** `tweaks/custom/utils/authentication.py`

**What it patches:**
- `frappe.auth.validate_api_key_secret`

**Purpose:**
- Allows using username/password for API authentication in addition to API key/secret
- Useful for simplified API authentication during development or specific use cases

**Current Implementation:**
```python
def apply_authentication_patches():
    auth.validate_api_key_secret = decorate_validate_api_key_secret(
        auth.validate_api_key_secret
    )
```

**Migration Strategy:**

**Option 1: Direct Integration**
1. Modify `frappe/auth.py`:
   - Update `validate_api_key_secret` to support username/password fallback
   - Add a setting to enable/disable this feature

**Option 2: Hook-based Approach**
2. Add new hook in `frappe/auth.py`:
   - `validate_api_credentials` - called before standard API key validation
   - Allow apps to provide alternative authentication methods

**Files to Modify in Frappe:**
- `frappe/auth.py`

**Recommended Approach:**
- Option 2 (Hook-based) is safer and more flexible
- Allows other apps to provide alternative authentication methods
- Add a system setting to enable/disable this feature

---

### 5. Database Query Enhancements

**Location:** `tweaks/custom/utils/db_query.py`

**What it patches:**
- `frappe.model.db_query.DatabaseQuery.build_match_conditions`
- `frappe.model.db_query.DatabaseQuery.get_permission_query_conditions`

**Purpose:**
- Enables shared documents when permission query conditions are present
- Caches permission query conditions to avoid redundant computation

**Current Implementation:**
```python
def apply_db_query_patches():
    DatabaseQuery.build_match_conditions = build_match_conditions(
        DatabaseQuery.build_match_conditions
    )
    DatabaseQuery.get_permission_query_conditions = get_permission_query_conditions(
        DatabaseQuery.get_permission_query_conditions
    )
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/model/db_query.py`:
   - Update `build_match_conditions` to set `_fetch_shared_documents` flag
   - Add caching to `get_permission_query_conditions`

**Files to Modify in Frappe:**
- `frappe/model/db_query.py`

**Implementation Notes:**
- The patch improves performance by caching permission query conditions
- The shared documents feature should be configurable

---

### 6. User Group Rename Permission

**Location:** `tweaks/custom/doctype/user_group.py`

**What it patches:**
- Sets `allow_rename` property for User Group doctype

**Purpose:**
- Allows renaming User Groups

**Current Implementation:**
```python
def apply_user_group_patches():
    make_property_setter(
        "User Group", None, "allow_rename", "1", "Check", for_doctype=True
    )
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/core/doctype/user_group/user_group.json`:
   - Set `"allow_rename": 1` in the doctype definition

**Files to Modify in Frappe:**
- `frappe/core/doctype/user_group/user_group.json`

---

### 7. Role Rename Permission

**Location:** `tweaks/custom/doctype/role.py`

**What it patches:**
- Sets `allow_rename` property for Role doctype

**Purpose:**
- Allows renaming Roles

**Current Implementation:**
```python
def apply_role_patches():
    make_property_setter(
        "Role", None, "allow_rename", "1", "Check", for_doctype=True
    )
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/core/doctype/role/role.json`:
   - Set `"allow_rename": 1` in the doctype definition

**Files to Modify in Frappe:**
- `frappe/core/doctype/role/role.json`

---

## Doctype Overrides

### 8. TweaksServerScript (Server Script Override)

**Location:** `tweaks/custom/doctype/server_script.py`

**What it overrides:**
- `frappe.core.doctype.server_script.server_script.ServerScript`

**Purpose:**
- Adds validation for new script types (Permission Policy, Permission Query)
- Adds `get_permission_policy` method for Permission Policy scripts

**Current Implementation:**
```python
override_doctype_class = {
    "Server Script": "tweaks.custom.doctype.server_script.TweaksServerScript",
}
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/core/doctype/server_script/server_script.py`:
   - Add the enhanced validation logic from `TweaksServerScript`
   - Add the `get_permission_policy` method

**Files to Modify in Frappe:**
- `frappe/core/doctype/server_script/server_script.py`

---

### 9. TweaksReminder (Reminder Override)

**Location:** `tweaks/custom/doctype/reminder.py`

**What it overrides:**
- `frappe.automation.doctype.reminder.reminder.Reminder`

**Purpose:**
- Enhanced reminder sending with better notification handling
- Sends both notification log and email

**Current Implementation:**
```python
override_doctype_class = {
    "Reminder": "tweaks.custom.doctype.reminder.TweaksReminder",
}
```

**Migration Strategy:**

**Direct Integration (Recommended)**
1. Modify `frappe/automation/doctype/reminder/reminder.py`:
   - Update the `send_reminder` method with the enhanced logic

**Files to Modify in Frappe:**
- `frappe/automation/doctype/reminder/reminder.py`

---

## Custom Hooks and Features

### 10. Permission Policy System

**Location:** `tweaks/custom/utils/permissions.py`

**What it provides:**
- Custom permission system using Server Scripts
- `has_permission` hook implementation
- `permission_query_conditions` hook implementation

**Purpose:**
- Allows defining complex permission rules via Server Scripts
- Provides fine-grained access control

**Current Implementation:**
```python
permission_hooks = {
    "permission_query_conditions": {
        "*": ["tweaks.custom.utils.permissions.get_permission_policy_query_conditions"]
    },
    "has_permission": {
        "*": ["tweaks.custom.utils.permissions.has_permission_policy"]
    },
}
```

**Migration Strategy:**

**Integration as Core Feature**
1. This is a new feature, not a monkeypatch
2. Consider adding it as a core Frappe feature
3. Integrate with the Server Script enhancements (item #2)

**Files to Add in Frappe:**
- `frappe/permissions/policy.py` (new file for permission policy logic)

**Files to Modify in Frappe:**
- `frappe/permissions.py` - integrate with existing permission system
- Update hooks to call permission policy functions

---

### 11. Pricing Rule Enhancements (ERPNext)

**Location:** `tweaks/custom/doctype/pricing_rule.py`

**What it provides:**
- Dynamic free item calculation via Python scripts
- Dynamic pricing rule validation via Python scripts

**Purpose:**
- Allows complex pricing logic to be defined in Pricing Rules
- Adds hooks for pricing rule customization

**Current Implementation:**
```python
get_product_discount_rule = [
    "tweaks.custom.doctype.pricing_rule.get_product_discount_rule"
]

apply_pricing_rule_on_transaction = [
    "tweaks.custom.doctype.pricing_rule.apply_pricing_rule_on_transaction"
]
```

**Migration Strategy:**

**Integration as ERPNext Feature**
1. This should be migrated to ERPNext, not Frappe
2. Add custom fields to Pricing Rule doctype
3. Integrate hooks into pricing rule logic

**Files to Modify in ERPNext:**
- `erpnext/accounts/doctype/pricing_rule/pricing_rule.json` - add custom fields
- `erpnext/accounts/doctype/pricing_rule/utils.py` - integrate hooks

**Custom Fields to Add:**
- `dynamic_free_item` (Code, Python)
- `dynamic_validation` (Code, Python)

---

## Migration Priority

### High Priority (Core Functionality)
1. **Server Script Enhancements** (#2) - Most significant feature enhancement
2. **Document.run_method** (#1) - Foundation for Server Scripts
3. **Workflow Enhancements** (#3) - Critical workflow features

### Medium Priority (Quality of Life)
4. **Database Query Enhancements** (#5) - Performance improvement
5. **Permission Policy System** (#10) - Advanced permission features
6. **TweaksServerScript Override** (#8) - Part of Server Script system

### Low Priority (Minor Features)
7. **Authentication Enhancement** (#4) - Development convenience
8. **TweaksReminder Override** (#9) - Minor improvement
9. **User Group Rename** (#6) - Cosmetic feature
10. **Role Rename** (#7) - Cosmetic feature
11. **Pricing Rule Enhancements** (#11) - ERPNext-specific

---

## Migration Checklist

### Pre-Migration
- [ ] Create a new branch in your Frappe fork
- [ ] Create a new branch in your ERPNext fork (for pricing rules)
- [ ] Set up development environment with forked versions
- [ ] Document current behavior with tests

### Migration Process
- [ ] Migrate Server Script enhancements (#2, #8)
- [ ] Migrate Document.run_method (#1)
- [ ] Migrate Workflow enhancements (#3)
- [ ] Migrate Database Query enhancements (#5)
- [ ] Migrate Permission Policy system (#10)
- [ ] Migrate Authentication enhancement (#4)
- [ ] Migrate Reminder override (#9)
- [ ] Migrate User Group rename (#6)
- [ ] Migrate Role rename (#7)
- [ ] Migrate Pricing Rule enhancements to ERPNext (#11)

### Post-Migration
- [ ] Update `frappe_tweaks` app to remove monkeypatches
- [ ] Add compatibility flags for older Frappe versions
- [ ] Update documentation
- [ ] Test all features thoroughly
- [ ] Deploy to staging environment
- [ ] Deploy to production

---

## Testing Strategy

After migrating each monkeypatch:

1. **Unit Tests**: Add unit tests in Frappe/ERPNext for the new functionality
2. **Integration Tests**: Test with existing `frappe_tweaks` doctypes
3. **Regression Tests**: Ensure existing Frappe functionality isn't broken
4. **Performance Tests**: Verify no performance degradation

---

## Backward Compatibility

If you need to maintain backward compatibility with standard Frappe:

1. Keep the monkeypatches in `frappe_tweaks`
2. Add version detection:
   ```python
   if not hasattr(Document, 'get_method_args'):
       # Apply patch only if not in forked version
       apply_document_patches()
   ```

3. Use feature flags:
   ```python
   if frappe.get_system_settings('enable_enhanced_server_scripts'):
       # Use new features
   ```

---

## Notes

- All monkeypatches are currently applied when the app initializes via `tweaks/__init__.py`
- The Event Script feature is deprecated and should not be migrated (see `tweaks/tweaks/doctype/event_script/`)
- Some features require database schema changes (custom fields, property setters)
- Consider creating migration patches in Frappe for smooth upgrades

## Non-Monkeypatch Features

The following files in `tweaks/custom/` are NOT monkeypatches and don't need migration:

1. **`customer.js`** - Custom Quick Entry Form for SUNAT (Peru) customer creation
   - This is app-specific functionality, keep in `frappe_tweaks`
   
2. **`hooks.js`** - JavaScript utility functions for hook execution
   - These are utility functions, not monkeypatches
   - Keep in `frappe_tweaks` or consider contributing to Frappe as utilities

3. **`customize_form.py`** - Utility for setting property setters
   - Helper function, not a monkeypatch
   - Keep in `frappe_tweaks`

4. **`customer.py`** - Customer-specific validation and business logic
   - App-specific business logic using doc_events hooks
   - Keep in `frappe_tweaks`

5. **`naming.py`** - Utility function for series management
   - Helper function for naming series
   - Keep in `frappe_tweaks` or consider contributing to Frappe

6. **`formatter.py`** - String formatting utilities
   - General utility function
   - Keep in `frappe_tweaks`

---

## Summary

**Total Monkeypatches: 9**
- 5 function/method patches
- 2 doctype class overrides  
- 2 property setters

**Total New Features: 2**
- Permission Policy system (hooks-based)
- Pricing Rule enhancements (hooks-based)

**Files NOT to migrate: 6**
- Utility functions and app-specific logic

---

## Contact

For questions about specific monkeypatches or migration strategies, refer to:
- Original code in `tweaks/custom/patches.py`
- Individual patch files in `tweaks/custom/doctype/` and `tweaks/custom/utils/`
- This documentation: `MONKEYPATCH_MIGRATION.md`
