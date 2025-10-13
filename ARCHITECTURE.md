# Architecture Documentation

## Overview

Frappe Tweaks is a comprehensive extension app for the Frappe Framework that provides advanced features for access control, event scripting, business logic management, and core framework enhancements. The app is designed with modularity and extensibility in mind.

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frappe Framework                         │
└─────────────────────────────────────────────────────────────┘
                          ↑
                          │ Hooks & Patches
                          │
┌─────────────────────────────────────────────────────────────┐
│                    Frappe Tweaks App                         │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │  Core Module   │  │ Custom Module  │  │ Utils Module  │ │
│  │  (tweaks/)     │  │ (custom/)      │  │ (utils/)      │ │
│  └────────────────┘  └────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Access Control (AC) Module

A hierarchical, rule-based access control system that provides fine-grained permissions beyond Frappe's standard role-based access control.

#### Components:

**AC Principal** (`ac_principal.py`)
- Represents who can access resources (users, roles, groups, or custom scripts)
- Uses NestedSet for hierarchical organization
- Types: User, Role, User Group, User Script
- Supports both SQL and Python scripts for dynamic principal resolution

**AC Resource** (`ac_resource.py`)
- Represents what can be accessed (DocTypes, Reports, Custom resources)
- Uses NestedSet for hierarchical organization
- Types: DocType, Report, Custom, Child
- Field-level access control with `fieldname` attribute
- Condition scripts (SQL or Python) for dynamic resource filtering

**AC Rule** (`ac_rule.py`)
- Combines principals and resources with actions
- Supports recursive rules (apply to child nodes)
- Exception handling (exclude specific principals/resources)
- Validates that all resources belong to the same root

**AC Action** (`ac_action.py`)
- Standard actions: Read, Write, Create, Delete, Submit, Cancel, Select, Amend, Print, Email, Report, Import, Export, Share
- At least one action must be enabled at all times
- Support for both standard and custom actions

#### Data Flow:

```
User Request → AC Rule Check → Principal Resolution → Resource Resolution → Action Validation → Allow/Deny
```

#### Key Functions:

- `has_permissions()`: Main permission check function
- `get_rule_map()`: Cached rule mapping for performance
- `get_resource_rules()`: Fetch applicable rules for a resource
- `resolve_principals()`: Convert principal definitions to SQL/script conditions
- `resolve_resources()`: Convert resource definitions to SQL/script conditions

### 2. Event Script System

A powerful system for executing custom Python scripts on document lifecycle events.

#### Architecture:

```
Document Event → get_script_map() → Filter by User/Role → Resolve Parameters → Execute Scripts (by priority)
```

#### Components:

**Event Script** (`event_script.py`)
- Defines when and what scripts to execute
- Filters: Document Type, Document Type Group, User, User Group, Role, Role Profile
- Events: Standard lifecycle events + workflow transitions + permission events
- Priority-based execution (higher priority = executed first)
- Parameter system for injecting data from other documents

**Event Script Parameter** (`event_script_parameter.py`)
- Child table for passing parameters to scripts
- Supports fetching data from any DocType
- Field selection for specific values

#### Caching Strategy:

- Script map cached in `frappe.cache` with key `event_script_map`
- Cache invalidated on Event Script changes
- Key format: `{doctype}:{event}:{action}:{workflow_action}`

#### Script Execution Context:

Scripts have access to:
- `doc`: Current document
- `doctype`: Document type
- `user`: Current user
- `parameters`: Resolved parameter values
- `event`: Event name
- `event_args`: Event-specific arguments
- `allow`, `filters`, `or_filters`, `message`: For permission scripts

### 3. Business Logic Module

Centralized repository for managing business rules and linking them to documents.

#### Components:

**Business Logic** (`business_logic.py`)
- Central entity for business rules
- Auto-naming: `BL-{category_series}-{year}-`
- Links to multiple documents via Business Logic Link

**Business Logic Category** (`business_logic_category.py`)
- Categorization for business logic
- Custom naming series per category

**Business Logic Link** (`business_logic_link.py`)
- Links business logic to any document
- Tracks document titles for easy reference

### 4. DocType Group System

**DocType Group** (`doctype_group.py`)
- Groups related DocTypes for batch operations
- Used by Event Scripts to apply scripts to multiple DocTypes

**DocType Group Member** (`doctype_group_member.py`)
- Child table linking DocTypes to groups

## Custom Module (Frappe Core Extensions)

### Patching System

All patches are applied during app initialization in `__init__.py`:

```python
from tweaks.custom.patches import apply_patches
apply_patches()
```

### Key Patches:

#### 1. Server Script Enhancements (`server_script_customization.py`)

**Added Fields:**
- `title`: Human-readable title (required)
- `reference_script`: Link to another script
- `priority`: Execution order for DocType Events
- `description`: Documentation field

**Modified Properties:**
- Auto-naming changed to hash-based
- Title field becomes the display field
- Modified script types and event options

**Patched Functions:**
- `get_server_script_map()`: Enhanced mapping with priority support
- `run_server_script_for_doc_event()`: Priority-based execution

#### 2. Workflow Enhancements (`workflow.py`)

**Added Features:**
- `auto_apply` field on Workflow Transition
- Auto-transition logic on document change
- Enhanced `get_transitions()` and `apply_workflow()` functions

**Hook Integration:**
```python
doc_events: {
    "*": {
        "on_change": ["tweaks.custom.doctype.workflow.on_change"]
    }
}
```

#### 3. Client Script Patches (`client_script.py`)

Extends client scripts with additional functionality.

#### 4. Safe Execution Environment (`safe_exec.py`)

**Enhanced Global Context:**
- `re` module with safe methods
- `frappe.cache` module
- `frappe.call` for whitelisted functions
- `frappe.db.unsafe_sql` for admin users
- Additional utility functions
- YAML support
- Excel file reading support

**Patching Method:**
```python
def get_safe_globals(get_safe_globals):
    def _get_safe_globals():
        globals = get_safe_globals()
        # Add overrides
        return globals
    return _get_safe_globals
```

#### 5. Authentication Patches (`authentication.py`)

Custom authentication enhancements.

#### 6. Database Query Patches (`db_query.py`)

Enhanced database query capabilities.

#### 7. Fixtures Management (`fixtures.py`)

Improved fixture handling for development.

#### 8. Permissions System (`permissions.py`)

Extended permission checking integrated with AC Module and Event Scripts.

#### 9. Virtual DocType Support (`virtual_doctype.py`)

Support for virtual DocTypes (DocTypes without database tables).

## Utilities Module

### Query Report Utilities (`query_report.py`)
Helper functions for building and executing query reports.

### Groupby Operations (`groupby.py`)
Advanced grouping operations for data aggregation.

### Changelog Tracking (`changelog.py`)
Version tracking and changelog management.

### Access Control Helpers (`access_control.py`)
Core helper for permission evaluation:
```python
@site_cache
def allow_value():
    if frappe_version() <= 15:
        return None  # Fallthrough to other hooks
    return True
```

### Preflight Checks (`preflight.py`)
Pre-execution validation checks.

## Hooks System

The app integrates with Frappe using various hooks defined in `hooks.py`:

### After Install Hooks
- Install pricing rule customizations
- Apply user group patches
- Apply role patches
- Install standard AC actions
- Install workflow, client script, and server script fields

### Doc Events Hooks
- Workflow auto-transition on change

### Permission Hooks
- Event Script permission checks
- AC Module permission checks

### Override Hooks
- Whitelisted methods override
- DocType class overrides (Client Script, Server Script, Reminder)
- Pricing rule functions

## Performance Considerations

### Caching Strategy

1. **Script Map Caching**
   - Event scripts cached by key
   - Invalidated on script changes
   - Site-level cache using `frappe.cache`

2. **Rule Map Caching**
   - AC rules cached for performance
   - Request-level cache using `@frappe.request_cache`

3. **Permission Query Caching**
   - `allow_value()` uses `@site_cache`

### Query Optimization

1. **Nested Set Queries**
   - AC Principal and AC Resource use NestedSet for efficient hierarchy queries
   - Left/Right indexing for fast descendant/ancestor queries

2. **Batch Loading**
   - Scripts loaded in batch, ordered by priority
   - Resources resolved in single queries where possible

3. **Early Exit Patterns**
   - Administrator bypass for permission checks
   - Empty policy sets return early

## Data Flow Examples

### Permission Check Flow

```
1. User requests document access
2. Check if user is Administrator → Allow
3. Get Event Script policies → Execute permission scripts
4. Get AC Rule policies → Resolve principals → Resolve resources
5. Combine policies (AND logic)
6. Return allow/deny with message
```

### Event Script Execution Flow

```
1. Document event triggered (e.g., before_save)
2. Load script map from cache
3. Get scripts for doctype:event key
4. Filter by user/role/group
5. Sort by priority (descending)
6. For each script:
   - Resolve parameters
   - Create execution context
   - Execute with safe_exec
7. Continue or abort based on exceptions
```

### AC Rule Resolution Flow

```
1. Request with resource parameters (doctype, action, user)
2. Load rule map from cache
3. Get params (resource key, action, user)
4. Find matching rules
5. For each rule:
   - Resolve principals → SQL conditions or scripts
   - Resolve resources → SQL conditions or scripts
   - Check exceptions
6. Build final SQL condition
7. Execute permission query
8. Return allowed resources
```

## Security Considerations

1. **Safe Execution Environment**
   - Scripts executed in restricted context
   - Limited global namespace
   - No dangerous builtins (eval, exec, open, etc.)
   - Admin-only for unsafe operations

2. **Permission Layering**
   - Multiple permission systems work together (AND logic)
   - Event Scripts can restrict beyond AC Rules
   - Role-based access still applies

3. **Script Validation**
   - Scripts validated before execution
   - Error logging for failed scripts
   - Non-throwing execution option for permission checks

4. **Standard Protection**
   - Standard resources protected in production
   - Developer mode required for modifying standard AC Resources
   - Cannot delete last enabled AC Action

## Testing Strategy

Each module includes test files:
- `test_ac_action.py`
- `test_ac_principal.py`
- `test_ac_resource.py`
- `test_ac_rule.py`
- `test_event_script.py`
- `test_business_logic.py`

Tests cover:
- CRUD operations
- Validation logic
- Permission checks
- Script execution
- Cache invalidation
- Nested set operations

## Extension Points

The architecture is designed for extensibility:

1. **Custom AC Actions**: Add domain-specific actions
2. **Custom Resources**: Define custom resource types
3. **Custom Principals**: Script-based principal resolution
4. **Event Script Parameters**: Pass any data to scripts
5. **Workflow Transitions**: Custom auto-apply logic
6. **Safe Exec Extensions**: Add more modules to global context

## Future Considerations

Areas marked with TODO comments indicate potential optimization opportunities:
- Performance improvements for large datasets
- Additional caching strategies
- Query optimization for complex hierarchies
- Batch operations for rule resolution
- Enhanced script debugging tools
