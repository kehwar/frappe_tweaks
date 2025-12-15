# Monkeypatch Quick Reference

This is a quick reference guide for the monkeypatches in `frappe_tweaks`. For detailed migration instructions, see [MONKEYPATCH_MIGRATION.md](./MONKEYPATCH_MIGRATION.md).

## At a Glance

| # | What | Where | Priority | Frappe File(s) to Modify |
|---|------|-------|----------|--------------------------|
| 1 | Document.run_method | `custom/doctype/document.py` | HIGH | `frappe/model/document.py` |
| 2 | Server Script System | `custom/doctype/server_script_customization.py` | HIGH | `frappe/core/doctype/server_script/*` |
| 3 | Workflow Auto-Apply | `custom/doctype/workflow.py` | HIGH | `frappe/model/workflow.py` |
| 4 | API Auth Fallback | `custom/utils/authentication.py` | LOW | `frappe/auth.py` |
| 5 | DB Query Cache | `custom/utils/db_query.py` | MEDIUM | `frappe/model/db_query.py` |
| 6 | User Group Rename | `custom/doctype/user_group.py` | LOW | `frappe/core/doctype/user_group/user_group.json` |
| 7 | Role Rename | `custom/doctype/role.py` | LOW | `frappe/core/doctype/role/role.json` |
| 8 | Server Script Class | `custom/doctype/server_script.py` | MEDIUM | `frappe/core/doctype/server_script/server_script.py` |
| 9 | Reminder Class | `custom/doctype/reminder.py` | LOW | `frappe/automation/doctype/reminder/reminder.py` |

## New Features (Not Monkeypatches)

| Feature | Where | Migrate To |
|---------|-------|------------|
| Permission Policy | `custom/utils/permissions.py` | Add to Frappe core permissions |
| Pricing Rule Dynamic | `custom/doctype/pricing_rule.py` | Add to ERPNext Pricing Rule |

## Patching Mechanism

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

## Migration Order

```
1. Server Script System (#2, #8)
   └─> Enable Server Script features
   
2. Document.run_method (#1)
   └─> Make Server Scripts work with doc events
   
3. Workflow Auto-Apply (#3)
   └─> Add workflow automation
   
4. DB Query Optimizations (#5)
   └─> Performance improvements
   
5. Permission Policies (new feature)
   └─> Advanced permissions
   
6. Minor Patches (#4, #6, #7, #9)
   └─> Quality of life improvements
   
7. ERPNext Features (#11)
   └─> Pricing rule enhancements
```

## Quick Migration Commands

### For Each Monkeypatch:

1. **Copy the enhanced code** from `tweaks/custom/` to the Frappe source
2. **Add custom fields** (if needed) to relevant doctypes
3. **Update tests** in Frappe to cover new functionality
4. **Remove from tweaks** once migrated to fork

### Example: Migrating Document.run_method

```bash
# In your Frappe fork
cd frappe/model
# Edit document.py, add enhanced run_method
# Add get_method_args and get_method_kwargs methods

# Test it works
bench --site dev.localhost run-tests --module frappe.model.document

# In frappe_tweaks
# Remove or comment out the patch
# Add version check to only patch if needed
```

## Testing Each Migration

```python
# In Frappe fork - add test like this:
def test_server_script_with_priority():
    # Create server scripts with different priorities
    # Verify they execute in correct order
    pass

def test_document_method_args():
    # Create a doc event
    # Verify get_method_args() returns correct values
    pass
```

## Files You Can Delete After Migration

Once all monkeypatches are in your Frappe/ERPNext fork:

- `tweaks/custom/patches.py`
- `tweaks/custom/doctype/document.py`
- `tweaks/custom/doctype/server_script_customization.py`
- `tweaks/custom/doctype/workflow.py`
- `tweaks/custom/utils/authentication.py`
- `tweaks/custom/utils/db_query.py`
- `tweaks/custom/doctype/user_group.py`
- `tweaks/custom/doctype/role.py`

Keep these (app-specific logic):
- `tweaks/custom/doctype/customer.py` (SUNAT integration)
- `tweaks/custom/doctype/pricing_rule.py` (becomes hook handlers)
- `tweaks/custom/utils/permissions.py` (becomes hook handlers)
- All utility files (naming.py, formatter.py, hooks.py, etc.)

## Backward Compatibility Check

Add this to `tweaks/__init__.py` after migration:

```python
import frappe
from frappe.model.document import Document

# Only apply patches if not in forked Frappe
if not hasattr(Document, 'get_method_args'):
    from tweaks.custom.patches import apply_patches
    apply_patches()
else:
    # Using forked Frappe with built-in enhancements
    frappe.log("Frappe fork detected, skipping monkeypatches")
```

## Questions?

See the detailed guide: [MONKEYPATCH_MIGRATION.md](./MONKEYPATCH_MIGRATION.md)
