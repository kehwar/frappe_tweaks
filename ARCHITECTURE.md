# Monkeypatch Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         frappe_tweaks App                               │
│                                                                         │
│  tweaks/__init__.py                                                     │
│       │                                                                 │
│       └─> custom/patches.py::apply_patches()                           │
│                                                                         │
└─────────────────────┬───────────────────────────────────────────────────┘
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌──────────┐ ┌────────────┐
│   Document  │ │  Server  │ │  Workflow  │
│   Patches   │ │  Script  │ │  Patches   │
│             │ │  Patches │ │            │
└──────┬──────┘ └─────┬────┘ └──────┬─────┘
       │              │              │
       │              │              │
       ▼              ▼              ▼
┌──────────────────────────────────────────────┐
│           Frappe Core Framework              │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  frappe.model.document               │   │
│  │    • run_method() ◄────────┐         │   │
│  │    • get_method_args()     │         │   │
│  │    • get_method_kwargs()   │         │   │
│  └────────────────────────────┼─────────┘   │
│                                │             │
│  ┌────────────────────────────┼─────────┐   │
│  │  frappe.core.doctype       │         │   │
│  │    .server_script          │         │   │
│  │    • get_server_script_map()         │   │
│  │    • run_server_script_for_doc_event │   │
│  │    • TweaksServerScript ◄────────────┤   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  frappe.model.workflow               │   │
│  │    • get_transitions()               │   │
│  │    • apply_workflow() ◄──────────────┤   │
│  │    • apply_workflow_transition()     │   │
│  │    • apply_auto_workflow_transition()│   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  frappe.auth                         │   │
│  │    • validate_api_key_secret() ◄─────┤   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │  frappe.model.db_query               │   │
│  │    • build_match_conditions() ◄──────┤   │
│  │    • get_permission_query_conditions │   │
│  └──────────────────────────────────────┘   │
│                                              │
└──────────────────────────────────────────────┘
```

## Current Flow (With Monkeypatches)

```
User Action (e.g., Save Document)
         │
         ▼
frappe.model.document.Document.save()
         │
         ▼
document.run_method("validate")  ◄── MONKEYPATCHED
         │
         ├─> Original Frappe hooks
         ├─> Webhooks
         ├─> Server Scripts ◄─────────────── ENHANCED
         └─> Event Scripts (deprecated)
              │
              ▼
       Server Script Execution
              │
              ├─> DocType Events ◄────────── ENHANCED (priority, new events)
              ├─> Permission Policies ◄────── NEW FEATURE
              └─> Permission Queries ◄─────── NEW FEATURE
```

## After Migration Flow (In Fork)

```
User Action (e.g., Save Document)
         │
         ▼
frappe.model.document.Document.save()
         │
         ▼
document.run_method("validate")  ◄── NATIVE (no patch needed)
         │
         ├─> Original Frappe hooks
         ├─> Webhooks
         ├─> Server Scripts ◄─────────────── NATIVE (built-in)
         └─> [Event Scripts removed]
              │
              ▼
       Server Script Execution
              │
              ├─> DocType Events (with priority)
              ├─> Permission Policies
              └─> Permission Queries
```

## Workflow Enhancement Flow

```
Document Change
      │
      ▼
workflow.on_change() ◄── Hook from frappe_tweaks
      │
      ▼
apply_auto_workflow_transition()  ◄── NEW FUNCTION
      │
      ├─> Check for auto_apply transitions
      │
      └─> If found, apply_workflow_transition()
               │
               ├─> doc.before_transition(transition)  ◄── NEW HOOK
               ├─> Update workflow state
               ├─> Save document
               └─> doc.after_transition(transition)  ◄── NEW HOOK
```

## Permission Policy Flow

```
has_permission(doc, user, ptype)
         │
         ▼
frappe.permissions.has_permission()
         │
         ├─> Standard permission checks
         │
         └─> Hook: has_permission_policy() ◄── FROM frappe_tweaks
                  │
                  ├─> Get Permission Policy scripts
                  ├─> Execute Server Scripts (Permission Policy type)
                  └─> Return allow/deny + custom message

permission_query_conditions(doctype)
         │
         ▼
DatabaseQuery.build_match_conditions()  ◄── MONKEYPATCHED
         │
         ├─> Standard conditions
         │
         └─> Hook: get_permission_policy_query_conditions()
                  │
                  ├─> Get Permission Query scripts
                  ├─> Execute Server Scripts (Permission Query type)
                  └─> Return SQL conditions
```

## Server Script Enhancement Details

### Current Frappe Server Script Types
```
1. DocType Event
2. Scheduler Event
3. API
```

### Enhanced Server Script Types (frappe_tweaks)
```
1. DocType Event ◄────────── ENHANCED (more events, priority)
2. Scheduler Event
3. API
4. Permission Policy ◄──────── NEW
5. Permission Query ◄───────── NEW
```

### Enhanced EVENT_MAP
```
Standard Events (Frappe):
  • Before Insert, After Insert
  • Before Save, After Save
  • Before Submit, After Submit
  • Before Cancel, After Cancel
  • Before Delete, After Delete

Additional Events (frappe_tweaks):
  • Before Rename, After Rename
  • Before Print
  • On Payment Authorization
  • Before Transition, After Transition  ◄─ Workflow
  • Before Change, After Change  ◄───────── Generic change detection
  • Before/After Save (Submitted Document)
```

## Migration Dependency Graph

```
Priority 1 (Must migrate first):
┌────────────────────────────────┐
│  Server Script Enhancements    │ ◄── Foundation for everything
└────────────┬───────────────────┘
             │
Priority 2 (Depends on #1):
             ├──► Document.run_method ◄── Uses Server Scripts
             │
Priority 3 (Can be parallel):
             ├──► Workflow Enhancements
             ├──► Permission Policies
             ├──► DB Query Cache
             │
Priority 4 (Independent):
             ├──► Auth Enhancement
             ├──► User Group Rename
             ├──► Role Rename
             └──► Reminder Override
```

## File Relationships

```
frappe_tweaks/
│
├── tweaks/__init__.py
│   └─ Calls apply_patches()
│
├── tweaks/custom/patches.py
│   └─ Central patch orchestrator
│
├── tweaks/custom/doctype/
│   ├── document.py ────────────► frappe/model/document.py
│   ├── server_script.py ───────► frappe/core/doctype/server_script/
│   ├── server_script_customization.py ──► frappe/core/doctype/server_script/
│   ├── workflow.py ────────────► frappe/model/workflow.py
│   ├── role.py ────────────────► frappe/core/doctype/role/
│   ├── user_group.py ──────────► frappe/core/doctype/user_group/
│   └── reminder.py ────────────► frappe/automation/doctype/reminder/
│
├── tweaks/custom/utils/
│   ├── authentication.py ──────► frappe/auth.py
│   ├── db_query.py ────────────► frappe/model/db_query.py
│   └── permissions.py ─────────► frappe/permissions.py (NEW feature)
│
└── tweaks/custom/doctype/pricing_rule.py ──► erpnext/accounts/doctype/pricing_rule/
```

## Integration Points

### Hooks Used by frappe_tweaks

```yaml
override_doctype_class:
  - Server Script: TweaksServerScript
  - Reminder: TweaksReminder

doc_events:
  "*":
    on_change: [workflow auto-apply]
  "Customer":
    before_validate: [customer validation]
    validate: [customer validation]
    on_update: [customer update]

has_permission:
  "*": [Permission Policy check]

permission_query_conditions:
  "*": [Permission Policy query conditions]

get_product_discount_rule:
  - [Dynamic free item calculation]

apply_pricing_rule_on_transaction:
  - [Dynamic pricing validation]

safe_exec_globals:
  - [Additional safe exec globals]

safe_eval_globals:
  - [Additional safe eval globals]
```

### New Hooks to Add in Frappe Fork

```yaml
# Suggested new hooks after migration:

doc_event_hooks:
  before_doc_event: [Pre-processing before doc event]
  after_doc_event: [Post-processing after doc event]

server_script_hooks:
  filter_scripts: [Filter which scripts to run]
  before_script_execution: [Pre-script hook]
  after_script_execution: [Post-script hook]

workflow_hooks:
  before_transition: [Custom transition logic]
  after_transition: [Post-transition logic]
  auto_transition_check: [Custom auto-apply logic]

permission_hooks:
  permission_policy: [Custom permission policies]
  permission_query: [Custom query conditions]
```

---

## Legend

```
◄── : Patched/Modified by frappe_tweaks
──► : Should migrate to (in fork)
│   : Flow direction
┌─┐ : Component boundary
```
