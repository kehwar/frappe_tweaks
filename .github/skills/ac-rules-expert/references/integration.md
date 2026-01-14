# Integration with Frappe Permissions

This document explains how AC Rules integrate with Frappe's permission system for DocTypes, Reports, and future Workflow integration.

## Implementation Status

**Current State**:
- ✅ **DocTypes**: Fully implemented - Automatic permission enforcement via Frappe hooks
- ✅ **Reports**: Fully functional - Manual integration required (call API and inject SQL)
- 📋 **Workflows**: Planned but not yet implemented
- 🔄 **Migration Plan**: Migration from deprecated systems can now begin

**Deprecated Systems** (Do Not Use):
- ❌ **Event Scripts** - Legacy system, deprecated in favor of AC Rules
- ❌ **Server Script Permission Policy** - Legacy permission system, deprecated in favor of AC Rules

**Future Integration**:
- 📋 **Workflow Actions**: Planned integration to control workflow transitions dynamically
  - See: `.github/prompts/plan-integrate-ac-rules-with-workflow-actions.prompt.md`
  - Will enable AC Rules to manage workflow action permissions (e.g., approve, reject, submit)
  - Use cases include territory-based approvals, conditional validations, and complex approval logic
  - Implementation requires minimal Frappe core changes (hooks) + Tweaks integration

## DocType Integration (Automatic)

DocType integration is **fully available** and automatically enforces AC Rules through Frappe's permission query condition hooks.

### How It Works

Implemented in `tweaks/hooks.py`:

```python
permission_query_conditions = {
    "*": (
        event_script_hooks["permission_query_conditions"]["*"]
        + permission_hooks["permission_query_conditions"]["*"]
        + ["tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_permission_query_conditions"]
    )
}

write_permission_query_conditions = {
    "*": ["tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_write_permission_query_conditions"]
}
```

### Permission Query Conditions Hook

Filters list views and queries for read/select operations:
- Called by Frappe when loading list views and performing read queries
- Returns SQL WHERE clause to filter records based on AC Rules with action="read"
- Administrator always has full access
- Unmanaged resources return empty string (fall through to standard Frappe permissions)

### Write Permission Query Conditions Hook

Filters queries for write operations:
- Called by Frappe when performing write operations
- Accepts `ptype` parameter with actions: write, create, submit, cancel, delete
- Returns SQL WHERE clause to filter records based on AC Rules for the specified action
- Administrator always has full access
- Unmanaged resources return empty string (fall through to standard Frappe permissions)

### Implementation Details

- Both hooks use a shared internal helper function `_get_permission_query_conditions_for_doctype(doctype, user, action)`
- Actions are normalized using `scrub()` to ensure consistent formatting
- The write hook maps the ptype parameter to the appropriate AC Action using `scrub(ptype or "write")`

### Key Features

- Works alongside existing permission systems (Event Scripts, Server Script Permission Policy)
- Administrator always has full access
- Unmanaged doctypes fall through to standard Frappe permissions
- Supports Permit/Forbid rule logic
- Handles resource filters for both read and write operations
- **No manual integration required** for DocTypes (unlike Reports)

## Report Integration (Manual)

Reports must **manually** integrate AC Rules by calling the API to get filter queries.

### Integration Steps

1. Import the utility function
2. Call `get_resource_filter_query()` in your report
3. Check the access level
4. Inject the SQL filter into your query

### Example Implementation

```python
# In your report's get_data() or execute() function
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

def execute(filters=None):
    # Get AC Rule filter query for this report
    result = get_resource_filter_query(
        report="Your Report Name",
        action="read",
        user=frappe.session.user
    )
    
    # Build your SQL query with the AC Rule filter
    if result.get("access") == "none":
        return [], []  # User has no access
    
    ac_filter = result.get("query", "1=1")
    
    data = frappe.db.sql(f"""
        SELECT * FROM `tabYourDocType`
        WHERE {ac_filter}
        AND your_other_conditions
    """, as_dict=True)
    
    return columns, data
```

### Access Levels

The `access` field in the result can be:

- **total**: User has access to all records
  - Query = "1=1"
  - No filtering needed
  
- **partial**: User has conditional access
  - Query contains SQL WHERE clause
  - Must inject into report query
  
- **none**: User has no access
  - Query = "1=0"
  - Should return empty results
  
- **unmanaged**: Resource not managed by AC Rules
  - Query may be empty or "1=1"
  - Fall through to standard Frappe permissions

### Complete Example

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

def execute(filters=None):
    columns = get_columns()
    
    # Get AC Rule filter
    result = get_resource_filter_query(
        report="Sales Customer Report",
        action="read"
    )
    
    # Handle different access levels
    if result.get("access") == "none":
        return columns, []
    
    ac_filter = result.get("query", "1=1")
    
    # Build your query with AC filter
    conditions = []
    
    # Add report filters
    if filters.get("from_date"):
        conditions.append(f"creation >= '{filters.get('from_date')}'")
    if filters.get("to_date"):
        conditions.append(f"creation <= '{filters.get('to_date')}'")
    
    # Add AC filter
    conditions.append(f"({ac_filter})")
    
    where_clause = " AND ".join(conditions)
    
    data = frappe.db.sql(f"""
        SELECT 
            name,
            customer_name,
            account_manager,
            status,
            creation
        FROM `tabCustomer`
        WHERE {where_clause}
        ORDER BY creation DESC
    """, as_dict=True)
    
    return columns, data
```

## API Endpoints

All endpoints are whitelisted with `@frappe.whitelist()`:

### 1. Get Rule Map

```python
@frappe.whitelist()
def get_rule_map()
```

Returns the complete rule map structure.

### 2. Get Resource Rules

```python
@frappe.whitelist()
def get_resource_rules(
    resource="",      # AC Resource name
    doctype="",       # DocType name
    report="",        # Report name
    type="",          # "doctype" or "report"
    key="",           # DocType/Report name
    fieldname="",     # Optional field name
    action="",        # Action name (default: "read")
    user="",          # User (default: current user)
)
```

Returns rules that apply to a specific resource/action for a user.

**Response**:
```python
{
    "rules": [
        {
            "name": "ACL-2025-0001",
            "title": "Sales Team Read Access",
            "type": "Permit",
            "principals": [...],
            "resources": [...]
        }
    ],
    "unmanaged": False  # True if resource not managed by AC Rules
}
```

### 3. Get Resource Filter Query

```python
@frappe.whitelist()
def get_resource_filter_query(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
)
```

Returns the SQL WHERE clause for filtering records.

**Response**:
```python
{
    "query": "(status = 'Active') AND NOT (status = 'Archived')",
    "access": "partial",  # "total", "none", "partial", or "unmanaged"
    "unmanaged": False
}
```

### 4. Check Resource Access

```python
@frappe.whitelist()
def has_resource_access(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
)
```

Checks if a user has any access to a resource/action.

**Response**:
```python
{
    "access": True,
    "unmanaged": False
}
```

## Deprecated Systems

### Server Script Permission Policy (Deprecated)

Located in `tweaks/custom/utils/permissions.py` - **DO NOT USE**:

```python
# DEPRECATED - Do not use
permission_hooks = {
    "permission_query_conditions": {
        "*": ["tweaks.custom.utils.permissions.get_permission_policy_query_conditions"]
    },
    "has_permission": {
        "*": ["tweaks.custom.utils.permissions.has_permission_policy"]
    },
}
```

### Event Scripts (Deprecated)

- Location: `tweaks/tweaks/doctype/event_script/`
- Status: Deprecated in favor of AC Rules
- These will be removed as users migrate to AC Rules

### Migration Path

With DocType AC Rules now implemented, all permission logic should migrate to use AC Rules exclusively. The deprecated systems will be removed in a future release.

## Best Practices

1. **For DocTypes**: No integration needed - AC Rules are automatically enforced
2. **For Reports**: Always call `get_resource_filter_query()` and inject SQL
3. **Check access levels**: Handle "none", "partial", and "total" access appropriately
4. **Combine filters**: Use AND logic to combine AC filter with report filters
5. **Test thoroughly**: Verify access control works as expected for all user roles
6. **Monitor performance**: Complex filters may impact query performance
7. **Use appropriate actions**: Use "read" for reports, "write" for edits, etc.
8. **Handle unmanaged resources**: Fall back to standard Frappe permissions
