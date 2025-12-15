# Monkeypatch Migration Guide

This document lists all **actual monkeypatches** in the `frappe_tweaks` repository and how to migrate them to a Frappe/ERPNext fork.

**Note:** This document excludes features that use Frappe's standard hook system (`override_doctype_class`, `has_permission`, `permission_query_conditions`, `doc_events`, etc.) as these are not monkeypatches.

---

## 1. Document.run_method Enhancement

**Brief Description:** Extends `Document.run_method` to execute Server Scripts and Event Scripts on document events, and stores method arguments for later retrieval.

**Current Implementation:**
- Location: `tweaks/custom/doctype/document.py`
- Patches: `frappe.model.document.Document.run_method`
- Adds methods: `Document.get_method_args()`, `Document.get_method_kwargs()`

```python
def apply_document_patches():
    Document.run_method = run_method
    Document.get_method_args = get_method_args
    Document.get_method_kwargs = get_method_kwargs
```

The enhanced `run_method` calls:
1. Original Frappe hooks
2. Webhooks
3. Server Scripts via `run_server_script_for_doc_event()`
4. Event Scripts (deprecated)

**Proposed Migration:**
- **Target File:** `frappe/model/document.py`
- **Changes:**
  - Replace the existing `run_method` in the `Document` class with the enhanced version from `tweaks/custom/doctype/document.py`
  - Add `get_method_args` and `get_method_kwargs` as class methods
  - The enhanced version stores method args/kwargs in flags and calls Server Scripts after standard hooks

---

## 2. Server Script System Enhancement

**Brief Description:** Adds priority-based execution, new script types (Permission Policy, Permission Query), and extended event map with additional document events.

**Current Implementation:**
- Location: `tweaks/custom/doctype/server_script_customization.py` and `tweaks/custom/doctype/server_script_utils.py`
- Patches:
  - `frappe.core.doctype.server_script.server_script_utils.get_server_script_map`
  - `frappe.handler.get_server_script_map`
  - `frappe.model.db_query.get_server_script_map`
  - `frappe.core.doctype.server_script.server_script_utils.run_server_script_for_doc_event`
  - `frappe.model.document.run_server_script_for_doc_event`

```python
def apply_server_script_patches():
    server_script_utils.get_server_script_map = get_server_script_map
    handler.get_server_script_map = get_server_script_map
    db_query.get_server_script_map = get_server_script_map
    server_script_utils.run_server_script_for_doc_event = run_server_script_for_doc_event
    document.run_server_script_for_doc_event = run_server_script_for_doc_event
```

Extended EVENT_MAP includes: before_transition, after_transition, before_change, on_change, before_rename, after_rename, before_print, on_payment_authorized, etc.

**Proposed Migration:**
- **Target Files:**
  - `frappe/core/doctype/server_script/server_script.json` - Add custom fields
  - `frappe/core/doctype/server_script/server_script.py` - Add TweaksServerScript logic
  - `frappe/core/doctype/server_script/server_script_utils.py` - Replace functions with enhanced versions
  - `frappe/handler.py`, `frappe/model/db_query.py`, `frappe/model/document.py` - Update imports
- **Custom Fields to Add:**
  - `title` (Data, required) - Human-readable title
  - `reference_script` (Link to Server Script) - Reference to another script
  - `priority` (Int, default: 100) - Execution priority (higher runs first)
  - `description` (Text Editor) - Documentation
- **Property Setters:**
  - Set `autoname` to "hash"
  - Set `title_field` to "title"
  - Update `script_type` options to include "Permission Policy" and "Permission Query"
  - Update `doctype_event` options with extended EVENT_MAP

---

## 3. Workflow Auto-Apply Enhancement

**Brief Description:** Adds automatic workflow transitions and custom transition hooks (before_transition, after_transition).

**Current Implementation:**
- Location: `tweaks/custom/doctype/workflow.py`
- Patches: `frappe.model.workflow.get_transitions`, `frappe.model.workflow.apply_workflow`
- Adds functions: `apply_workflow_transition`, `apply_auto_workflow_transition`

```python
def apply_workflow_patches():
    workflow.get_transitions = get_transitions
    workflow.apply_workflow = apply_workflow
```

**Proposed Migration:**
- **Target Files:**
  - `frappe/model/workflow.py` - Replace `get_transitions` and `apply_workflow` with enhanced versions
  - `frappe/workflow/doctype/workflow_transition/workflow_transition.json` - Add custom field
- **Custom Fields to Add:**
  - Workflow Transition: `auto_apply` (Check) - Automatically apply transition when conditions are met
- **New Features:**
  - Document methods: `before_transition(transition)` and `after_transition(transition)` called during workflow transitions
  - Auto-apply workflow transitions via `on_change` event hook

---

## 4. Database Query Optimization

**Brief Description:** Improves performance by caching permission query conditions and enabling shared documents for queries with permission conditions.

**Current Implementation:**
- Location: `tweaks/custom/utils/db_query.py`
- Patches: `frappe.model.db_query.DatabaseQuery.build_match_conditions`, `frappe.model.db_query.DatabaseQuery.get_permission_query_conditions`

```python
def apply_db_query_patches():
    DatabaseQuery.build_match_conditions = build_match_conditions(DatabaseQuery.build_match_conditions)
    DatabaseQuery.get_permission_query_conditions = get_permission_query_conditions(DatabaseQuery.get_permission_query_conditions)
```

**Proposed Migration:**
- **Target File:** `frappe/model/db_query.py`
- **Changes:**
  - Update `build_match_conditions` to set `_fetch_shared_documents = True` when permission query conditions exist
  - Add caching to `get_permission_query_conditions` by storing result in `_permission_query_conditions` attribute

---

## 5. Authentication Fallback Enhancement

**Brief Description:** Allows username/password for API authentication in addition to API key/secret.

**Current Implementation:**
- Location: `tweaks/custom/utils/authentication.py`
- Patches: `frappe.auth.validate_api_key_secret`

```python
def apply_authentication_patches():
    auth.validate_api_key_secret = decorate_validate_api_key_secret(auth.validate_api_key_secret)
```

**Proposed Migration:**
- **Target File:** `frappe/auth.py`
- **Changes:**
  - Update `validate_api_key_secret` to try username/password authentication before falling back to API key validation
  - Add a system setting to enable/disable this feature for security
  - Alternative: Add a new hook `validate_api_credentials` for apps to provide custom authentication

---

## Migration Priority

**High Priority (Core Functionality):**
1. Server Script System Enhancement (#2)
2. Document.run_method Enhancement (#1)
3. Workflow Auto-Apply Enhancement (#3)

**Medium Priority (Quality of Life):**
4. Database Query Optimization (#4)
5. Authentication Fallback Enhancement (#5)

---

## Migration Checklist

### Pre-Migration
- [ ] Create branch in Frappe fork
- [ ] Set up development environment

### Migration Process (in priority order)
- [ ] Migrate Server Script enhancements (#2)
- [ ] Migrate Document.run_method (#1)
- [ ] Migrate Workflow enhancements (#3)
- [ ] Migrate Database Query optimizations (#4)
- [ ] Migrate Authentication enhancement (#5)

### Post-Migration
- [ ] Update `frappe_tweaks` to detect fork and skip patches
- [ ] Test all features
- [ ] Deploy to staging
- [ ] Deploy to production

---

## Backward Compatibility

After migration, update `tweaks/__init__.py` to detect the fork:

```python
import frappe
from frappe.model.document import Document

# Only apply patches if not in forked Frappe
if not hasattr(Document, 'get_method_args'):
    from tweaks.custom.patches import apply_patches
    apply_patches()
```

---

## How Patches Are Applied

All patches are applied through:
```
tweaks/__init__.py
  └─> custom/patches.py::apply_patches()
       ├─> apply_authentication_patches()
       ├─> apply_db_query_patches()
       ├─> apply_document_patches()
       ├─> apply_server_script_patches()
       └─> apply_workflow_patches()
```

