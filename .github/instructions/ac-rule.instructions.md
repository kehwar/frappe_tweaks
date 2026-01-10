---
description: 'Guidelines for working with AC Rules and Query Filters in Frappe Tweaks - an advanced access control system'
applyTo: '**/ac_rule/**, **/ac_resource/**, **/ac_principal/**, **/ac_action/**, **/query_filter/**, **/access_control.py, **/permissions.py'
---

# AC Rule and Query Filter System

Guidelines for working with the AC (Access Control) Rule and Query Filter system in Frappe Tweaks. This is an advanced access control framework that extends Frappe's built-in permission system with fine-grained, rule-based access control.

## Project Context

- **Technology**: Frappe Framework (Python + JavaScript)
- **Location**: `tweaks/tweaks/doctype/ac_*` and `tweaks/tweaks/doctype/query_filter`
- **Module**: Tweaks
- **Integration**: Manual integration required (automatic hooks not yet implemented)

## Implementation Status

**Current State**:
- ✅ **Reports**: Fully functional - Reports must manually call `get_resource_filter_query()` to get the SQL WHERE clause and inject it into the report query
- ✅ **DocTypes**: Fully implemented - Automatic permission enforcement for DocTypes via Frappe permission hooks
- 🔄 **Migration Plan**: Now that DocType integration is complete, migration from deprecated systems can begin

**Deprecated Systems** (Do Not Use):
- ❌ **Event Scripts** - Legacy system, deprecated in favor of AC Rules
- ❌ **Server Script Permission Policy** - Legacy permission system, deprecated in favor of AC Rules
- These will be removed as users migrate to AC Rules

## Overview

The AC Rule system provides advanced access control capabilities beyond Frappe's standard role-based permissions:

- **Fine-grained access control**: Control access at the record level, not just doctype level
- **Dynamic filtering**: Use SQL, Python, or JSON filters to determine access
- **Rule-based logic**: Define complex access rules with Permit/Forbid semantics
- **Principal-based**: Define who has access (users, roles, user groups, or custom logic)
- **Resource-based**: Define what is being accessed (doctypes, reports, or custom resources)
- **Action-based**: Control specific actions (read, write, delete, etc.)

## Core Components

### 1. AC Rule (Main DocType)

**Location**: `tweaks/tweaks/doctype/ac_rule/`

The AC Rule is the central component that ties everything together.

**Key Fields**:
- `title`: Human-readable name for the rule
- `type`: Either "Permit" or "Forbid"
- `resource`: Link to AC Resource (what is being accessed)
- `actions`: List of actions this rule applies to (read, write, delete, etc.)
- `principals`: Table of Query Filters defining who this rule applies to
- `resources`: Table of Query Filters defining which records this rule applies to
- `valid_from`/`valid_upto`: Optional date range for rule validity
- `disabled`: Flag to disable the rule

**Logic**:
```python
# Principal filtering (WHO has access)
allowed_users = (M1 OR M2) AND NOT (E1 OR E2)

# Resource filtering (WHAT records they can access)
allowed_records = (M1 OR M2) AND NOT (E1 OR E2)

# If no resource filters are defined, applies to ALL records
```

**Important Methods**:
- `validate()`: Validates rule configuration and resource filters
- `resolve_principals()`: Resolves principal filters into metadata
- `resolve_resources()`: Resolves resource filters into metadata
- `validate_resource_filters()`: Ensures filters match the resource's doctype/report

### 2. Query Filter

**Location**: `tweaks/tweaks/doctype/query_filter/`

Query Filters are reusable filter definitions that can be used in both principal and resource filtering.

**Key Fields**:
- `filter_name`: Human-readable name
- `reference_doctype`: DocType this filter applies to (e.g., "User", "Role", "Customer")
- `reference_docname`: Specific document name (for single-record filters)
- `reference_report`: Report this filter applies to
- `filters_type`: "JSON", "Python", or "SQL"
- `filters`: The actual filter code/definition

**Filter Types**:

1. **JSON Filters** (Default):
   - Uses Frappe's standard filter syntax
   - Example: `[["status", "=", "Active"]]`
   - Most common for doctype filtering
   - Automatically converted to SQL using `frappe.get_all()`

2. **SQL Filters**:
   - Direct SQL WHERE clause
   - Example: `status = 'Active' AND tenant_id = 1`
   - Used for complex conditions

3. **Python Filters**:
   - Python code that sets `conditions` variable
   - Example: `conditions = f"status = 'Active' AND tenant_id = {frappe.db.get_value('User', frappe.session.user, 'tenant_id')}"`
   - Used for dynamic filtering based on context

**Important Methods**:
- `get_sql()`: Converts filter to SQL WHERE clause
- Uses `@frappe.request_cache` for performance optimization

**SQL Generation Logic**:
```python
def get_sql(query_filter):
    if filters_type == "SQL":
        return filters  # Direct SQL
    
    if filters_type == "Python":
        # Execute Python code and return conditions variable
        safe_exec(filters, ...)
        return conditions
    
    if filters_type == "JSON":
        # Use frappe.get_all() to generate SQL
        sql = frappe.get_all(reference_doctype, filters=filters, run=0)
        return f"`tab{reference_doctype}`.`name` IN ({sql})"
```

### 3. AC Resource

**Location**: `tweaks/tweaks/doctype/ac_resource/`

Defines what is being accessed (the "resource").

**Resource Types**:
- **DocType**: Access control for a specific DocType
- **Report**: Access control for a specific Report

**Key Fields**:
- `type`: Type of resource
- `document_type`: DocType name (for DocType resources)
- `report`: Report name (for Report resources)
- `fieldname`: Optional field-level access control (Reports only)
- `managed_actions`: "All Actions" or "Select"
- `actions`: Table of specific actions (if "Select" is chosen)

**Important Limitations**:

⚠️ **Fieldname is NOT supported for DocType resources** - The `fieldname` field is automatically hidden when creating a DocType resource. Field-level access control is only available for Report resources. When type is set to "DocType", access control applies to the entire doctype, not individual fields.

### 4. AC Action

**Location**: `tweaks/tweaks/doctype/ac_action/`

Defines the actions that can be controlled (read, write, delete, create, etc.).

Standard actions are inserted on install via `after_install()` hook.

## Rule Map and Evaluation

### Rule Map Generation

**Function**: `get_rule_map()` in `ac_rule_utils.py`

The rule map is a hierarchical structure that organizes rules by resource and action:

```python
rule_map = {
    "doctype": {
        "Customer": {
            "": {  # fieldname (empty string = whole doctype)
                "read": [rule1, rule2, ...],
                "write": [rule1, rule2, ...],
                "delete": [...]
            }
        }
    },
    "report": {
        "Sales Report": {
            "": {
                "read": [rule1, rule2, ...]
            }
        }
    }
}
```

**Process**:
1. Load all enabled AC Resources
2. For each resource, create slots for managed actions
3. Load all valid, enabled AC Rules (within date range)
4. For each rule, resolve principals and resources
5. Add rule to appropriate slots in the map

### Permission Evaluation Flow

**Function**: `get_resource_rules()` in `ac_rule_utils.py`

1. **Get Rule Map**: Load the complete rule map (cached)

2. **Find Applicable Rules**: Look up rules for the specific resource/action

3. **Filter by User** (Principal Resolution):
   - For each rule, convert principal filters to SQL
   - Handle User, User Group, and Role reference doctypes specially
   - Execute SQL to check if current user matches any principals
   - Exclude exception principals

4. **Return Matching Rules**: Only rules where the user matches principals

**Function**: `get_resource_filter_query()` in `ac_rule_utils.py`

1. **Get User's Rules**: Call `get_resource_rules()` to get rules for user

2. **Build Resource Filter** (Resource Resolution):
   - For each rule, convert resource filters to SQL
   - Combine allowed and denied filters with AND/OR logic
   - Separate Permit and Forbid rules

3. **Combine Rules**:
   ```sql
   -- Final query structure
   (Permit1 OR Permit2 OR ...) AND NOT (Forbid1 OR Forbid2 OR ...)
   ```

4. **Return Query**: SQL WHERE clause that filters records

**Access Levels**:
- `total`: User has access to all records (query = "1=1")
- `none`: User has no access (query = "1=0")
- `partial`: User has conditional access (complex query)
- `unmanaged`: Resource not managed by AC Rules (full Frappe permissions apply)

### Principal Filter SQL Generation

**Function**: `get_principal_filter_sql(filter)` in `ac_rule_utils.py`

Special handling for different reference doctypes:

1. **User** (reference_doctype = "User"):
   ```python
   # Direct SQL from filter
   return filter.get_sql()
   ```

2. **User Group** (reference_doctype = "User Group"):
   ```python
   # Get matching user groups
   user_groups = frappe.db.sql(f"SELECT name FROM `tabUser Group` WHERE {sql}")
   
   # Get users in those groups
   sql = frappe.get_all("User Group Member", 
                       filters={"parent": ["in", user_groups]}, 
                       fields=["user"], run=0)
   
   return f"`tabUser`.`name` in ({sql})"
   ```

3. **Role** (reference_doctype = "Role"):
   ```python
   # Get matching roles
   roles = frappe.db.sql(f"SELECT name FROM `tabRole` WHERE {sql}")
   
   # Handle "All" role specially
   if "All" in roles:
       sql = frappe.get_all("User", run=0)
   else:
       sql = frappe.get_all("Has Role", 
                          filters={"role": ["in", roles]}, 
                          fields=["parent"], run=0)
   
   return f"`tabUser`.`name` in ({sql})"
   ```

### Resource Filter SQL Generation

**Function**: `get_resource_filter_sql(filter)` in `ac_rule_utils.py`

```python
if filter.get("all"):
    return "1=1"  # Match all records

if filter.get("name"):
    filter = frappe.get_cached_doc("Query Filter", filter.get("name"))
    return filter.get_sql()

return "1=0"  # Match nothing
```

## Integration with Frappe Permissions

**Current Implementation Status**:

### Reports (Implemented)

Reports must **manually** integrate AC Rules by calling the API to get filter queries:

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

**Important**: Each report must explicitly call `get_resource_filter_query()` and inject the returned SQL into its query.

### DocTypes (Implemented)

DocType integration is **now available** and automatically enforces AC Rules through Frappe's permission query condition hooks:

```python
# Implemented in tweaks/hooks.py
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

**How It Works**:

1. **Permission Query Conditions Hook**: Filters list views and queries for read/select operations
   - Called by Frappe when loading list views and performing read queries
   - Returns SQL WHERE clause to filter records based on AC Rules with action="read"
   - Administrator always has full access
   - Unmanaged resources return empty string (fall through to standard Frappe permissions)

2. **Write Permission Query Conditions Hook**: Filters queries for write operations
   - Called by Frappe when performing write operations
   - Accepts `ptype` parameter with actions: write, create, submit, cancel, delete
   - Returns SQL WHERE clause to filter records based on AC Rules for the specified action
   - Administrator always has full access
   - Unmanaged resources return empty string (fall through to standard Frappe permissions)

**Implementation Details**:
- Both hooks use a shared internal helper function `_get_permission_query_conditions_for_doctype(doctype, user, action)`
- Actions are normalized using `scrub()` to ensure consistent formatting
- The write hook maps the ptype parameter to the appropriate AC Action using `scrub(ptype or "write")`

**Key Features**:
- Works alongside existing permission systems (Event Scripts, Server Script Permission Policy)
- Administrator always has full access
- Unmanaged doctypes fall through to standard Frappe permissions
- Supports Permit/Forbid rule logic
- Handles resource filters for both read and write operations
- No manual integration required for DocTypes (unlike Reports)

### Deprecated Systems (Do Not Use)

The following systems in `tweaks/custom/utils/permissions.py` are **deprecated** and will be removed:

**1. Server Script Permission Policy** (Deprecated):
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

**2. Event Scripts** (Deprecated):
- Location: `tweaks/tweaks/doctype/event_script/`
- Status: Deprecated in favor of AC Rules
- These will be removed as users migrate to AC Rules

**Migration Path**: With DocType AC Rules now implemented, all permission logic should migrate to use AC Rules exclusively.

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

## Usage Examples

**Note**: AC Rules are fully functional for:
- **DocTypes**: Automatically enforced via Frappe permission hooks (no manual integration needed)
- **Reports**: Manual integration required - call `get_resource_filter_query()` and inject SQL into report queries

### Example 1: Sales Team Access Control (Report)

**Goal**: Create a Sales Report that only shows customers based on AC Rules.

**Step 1**: Create Query Filter for Sales Team Users
```
Filter Name: Sales Team Members
Reference Doctype: User
Filters Type: JSON
Filters: [["email", "like", "%@sales.company.com"]]
```

**Step 2**: Create Query Filter for Managed Customers
```
Filter Name: My Managed Customers
Reference Doctype: Customer
Filters Type: Python
Filters:
conditions = f"`tabCustomer`.`account_manager` = {frappe.db.escape(frappe.session.user)}"
```

**Step 3**: Create AC Resource
```
Type: Report
Report: Sales Customer Report
Managed Actions: Select
Actions: Read
```

**Step 4**: Create AC Rule
```
Title: Sales Team Read Managed Customers
Type: Permit
Resource: Sales Customer Report
Actions: Read
Principal Filters: Sales Team Members
Resource Filters: My Managed Customers
```

**Step 5**: Integrate in Report Code
```python
# In your report's execute() function
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

def execute(filters=None):
    # Get AC Rule filter
    result = get_resource_filter_query(
        report="Sales Customer Report",
        action="read"
    )
    
    if result.get("access") == "none":
        return [], []
    
    ac_filter = result.get("query", "1=1")
    
    # Use the filter in your query
    data = frappe.db.sql(f"""
        SELECT name, customer_name, account_manager
        FROM `tabCustomer`
        WHERE {ac_filter}
    """, as_dict=True)
    
    return columns, data
```

### Example 2: Restrict Archive Access (DocType)

**Goal**: Prevent all users from reading archived records.

**Step 1**: Create Query Filter for Archived Records
```
Filter Name: Archived Records
Reference Doctype: Customer
Filters Type: JSON
Filters: [["status", "=", "Archived"]]
```

**Step 2**: Create Query Filter for All Users
```
Filter Name: All Users
Reference Doctype: Role
Filters Type: JSON
Filters: [["name", "=", "All"]]
```

**Step 3**: Create AC Rule
```
Title: Forbid Archived Customer Access
Type: Forbid
Resource: Customer
Actions: Read
Principal Filters: All Users
Resource Filters: Archived Records
```

### Example 3: Tenant-Based Access

**Goal**: Multi-tenant setup where users only see their tenant's data.

**Step 1**: Create Query Filter for Tenant Users
```
Filter Name: Tenant Users
Reference Doctype: User
Filters Type: Python
Filters:
tenant_id = frappe.db.get_value("User", frappe.session.user, "tenant_id")
conditions = f"`tabUser`.`tenant_id` = {tenant_id}"
```

**Step 2**: Create Query Filter for Tenant Records
```
Filter Name: Tenant Sales Orders
Reference Doctype: Sales Order
Filters Type: Python
Filters:
tenant_id = frappe.db.get_value("User", frappe.session.user, "tenant_id")
conditions = f"`tabSales Order`.`tenant_id` = {tenant_id}"
```

**Step 3**: Create AC Rule
```
Title: Tenant Data Isolation
Type: Permit
Resource: Sales Order
Actions: Read, Write, Create, Delete
Principal Filters: Tenant Users
Resource Filters: Tenant Sales Orders
```

## Code Patterns and Best Practices

### 1. Creating Query Filters

**Pattern**: Reusable filters with clear names

```python
# Create a reusable principal filter
principal_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Sales Team",
    "reference_doctype": "User",
    "filters_type": "JSON",
    "filters": frappe.as_json([["department", "=", "Sales"]])
}).insert()

# Create a reusable resource filter
resource_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Active Customers",
    "reference_doctype": "Customer",
    "filters_type": "JSON",
    "filters": frappe.as_json([["status", "=", "Active"]])
}).insert()
```

### 2. Creating AC Rules

**Pattern**: Clear, descriptive rules with proper validation

```python
rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Sales Team Active Customer Access",
    "type": "Permit",
    "resource": "Customer",  # Must be created first
    "actions": [
        {"action": "Read"},
        {"action": "Write"}
    ],
    "principals": [
        {"filter": principal_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": resource_filter.name, "exception": 0}
    ]
})
rule.insert()
```

### 3. Using Exceptions

**Pattern**: Exclude specific users or records from a rule

```python
# Allow all sales team EXCEPT specific users
rule.principals = [
    {"filter": "Sales Team", "exception": 0},  # Include sales team
    {"filter": "Suspended Users", "exception": 1}  # Exclude suspended
]

# Allow all active customers EXCEPT VIP customers (handled differently)
rule.resources = [
    {"filter": "Active Customers", "exception": 0},  # Include active
    {"filter": "VIP Customers", "exception": 1}  # Exclude VIP
]
```

### 4. Dynamic Filters with Python

**Pattern**: Use current user context for filtering

```python
# Principal filter based on user metadata
filters = """
user_dept = frappe.db.get_value("User", frappe.session.user, "department")
conditions = f"`tabUser`.`department` = {frappe.db.escape(user_dept)}"
"""

# Resource filter based on user's assigned records
filters = """
user = frappe.session.user
conditions = f"`tabCustomer`.`account_manager` = {frappe.db.escape(user)}"
"""
```

### 5. Complex SQL Filters

**Pattern**: Multi-table joins or complex conditions

```python
# Resource filter with subquery
filters = """
customer_type IN (
    SELECT allowed_type 
    FROM `tabUser Permissions` 
    WHERE parent = '{user}'
) 
AND status != 'Cancelled'
"""

# Principal filter with EXISTS clause
filters = """
EXISTS (
    SELECT 1 
    FROM `tabTeam Member` tm
    WHERE tm.user = `tabUser`.`name`
    AND tm.team = 'Sales Team'
)
"""
```

### 6. Checking Access Programmatically

**Pattern**: Check before performing operations

```python
# Check if user has access to a resource
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access

result = has_resource_access(
    doctype="Customer",
    action="write",
    user=frappe.session.user
)

if result.get("access"):
    # User has write access to some customers
    pass
else:
    frappe.throw("You don't have write access to customers")

# Get filter query for listing
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

result = get_resource_filter_query(
    doctype="Customer",
    action="read"
)

if result.get("access") == "total":
    # User can see all customers
    customers = frappe.get_all("Customer")
elif result.get("access") == "partial":
    # Apply filter query
    query = result.get("query")
    customers = frappe.db.sql(f"""
        SELECT * FROM `tabCustomer`
        WHERE {query}
    """, as_dict=True)
else:
    # No access
    customers = []
```

## Performance Considerations

### 1. Request Caching

Query Filter's `get_sql()` uses `@frappe.request_cache` to cache SQL generation within a single request.

```python
@frappe.request_cache
def get_sql(query_filter: str | QueryFilter | dict):
    # Cached per request
    pass
```

### 2. Rule Map Caching

The rule map should be cached for performance. Consider implementing:

```python
@frappe.cache()  # Site-level cache
def get_rule_map():
    # Expensive operation - cache this
    pass
```

**Cache Invalidation**: Clear cache when:
- AC Rule is created/updated/deleted
- AC Resource is created/updated/deleted
- Query Filter is created/updated/deleted

### 3. SQL Query Optimization

- Ensure proper indexes on filtered fields
- Avoid complex Python filters when SQL/JSON will work
- Test generated SQL with EXPLAIN to check performance
- Consider materialized views for complex filters

### 4. Limit Rule Complexity

- Too many rules per resource/action slows evaluation
- Too many filters per rule increases SQL complexity
- Combine similar rules when possible
- Use exceptions sparingly

## Security Considerations

### 1. SQL Injection Prevention

**Always use proper escaping**:

```python
# GOOD - Using frappe.db.escape()
user = frappe.session.user
conditions = f"`tabCustomer`.`owner` = {frappe.db.escape(user)}"

# BAD - Direct interpolation
conditions = f"`tabCustomer`.`owner` = '{user}'"  # Vulnerable!
```

### 2. Python Filter Safety

Python filters use `safe_exec()` which provides a restricted environment:

```python
from frappe.utils.safe_exec import safe_exec

loc = {"resource": query_filter, "conditions": ""}
safe_exec(
    filters,
    None,
    loc,
    script_filename=f"Query Filter {query_filter.get('name')}"
)
```

**Restrictions**:
- No import statements
- Limited built-in functions
- Sandboxed environment

### 3. Permission Bypass Prevention

**Never allow**:
- Direct SQL execution without validation
- User-provided SQL in filters
- Disabling AC Rules without authorization

**Always**:
- Validate filter references match resource types
- Check user permissions before executing
- Log access attempts for audit trail

## Testing

### Unit Testing Query Filters

```python
def test_query_filter_json():
    qf = frappe.get_doc({
        "doctype": "Query Filter",
        "filter_name": "Active Users",
        "reference_doctype": "User",
        "filters_type": "JSON",
        "filters": frappe.as_json([["enabled", "=", 1]])
    })
    
    sql = qf.get_sql()
    assert "`tabUser`.`name` IN" in sql

def test_query_filter_sql():
    qf = frappe.get_doc({
        "doctype": "Query Filter",
        "filter_name": "Test SQL",
        "filters_type": "SQL",
        "filters": "status = 'Active'"
    })
    
    sql = qf.get_sql()
    assert sql == "status = 'Active'"
```

### Integration Testing AC Rules

```python
def test_ac_rule_evaluation():
    # Create test filters
    principal_filter = create_test_filter("Test Users", "User", ...)
    resource_filter = create_test_filter("Test Records", "Customer", ...)
    
    # Create test rule
    rule = create_test_rule(
        "Test Access",
        "Permit",
        principal_filter,
        resource_filter
    )
    
    # Test access
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access
    
    result = has_resource_access(
        doctype="Customer",
        action="read",
        user="test@example.com"
    )
    
    assert result.get("access") == True
```

### Testing Filter SQL Generation

```python
def test_principal_filter_sql():
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_principal_filter_sql
    
    # Test User filter
    user_filter = {"name": "user_filter", "reference_doctype": "User"}
    sql = get_principal_filter_sql(user_filter)
    assert sql
    
    # Test Role filter
    role_filter = {"name": "role_filter", "reference_doctype": "Role"}
    sql = get_principal_filter_sql(role_filter)
    assert "`tabUser`.`name` in" in sql
```

## Troubleshooting

### Issue: Rules Not Applying

**Check**:
1. Rule is not disabled
2. Rule is within valid date range (valid_from/valid_upto)
3. Resource is not disabled
4. Actions are properly configured on the resource
5. User matches at least one principal filter
6. Rule map is up to date (cache issue)

**Debug**:
```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_rules

result = get_resource_rules(
    doctype="Customer",
    action="read",
    user="test@example.com"
)

# Check the rules returned
print(result.get("rules"))
```

### Issue: Incorrect Filtering

**Check**:
1. Query Filter SQL is correct (use "Preview SQL" button)
2. Reference doctype matches the resource
3. Filter type (JSON/SQL/Python) is appropriate
4. Principal/Resource filters are not marked as exceptions incorrectly

**Debug**:
```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

result = get_resource_filter_query(
    doctype="Customer",
    action="read"
)

print(result.get("query"))  # Final WHERE clause
print(result.get("access"))  # Access level
```
print(result.get("parts"))  # Individual filter components
```

### Issue: Performance Problems

**Check**:
1. Too many rules per resource/action
2. Complex subqueries in filters
3. Missing database indexes
4. Python filters doing expensive operations
5. Rule map not cached

**Solutions**:
- Consolidate similar rules
- Add indexes to filtered fields
- Convert Python filters to SQL when possible
- Implement rule map caching
- Use EXPLAIN to analyze query performance

### Issue: Access Denied When Should Allow

**Check**:
1. Permit rule exists and is enabled
2. No Forbid rule is overriding it (Forbid takes precedence)
3. User matches principal filters
4. Record matches resource filters
5. Frappe's built-in permissions are also allowing access

**Remember**: AC Rules work alongside Frappe permissions, not instead of them.

## Common Mistakes

### 1. Forgetting Exception Logic

```python
# WRONG - Both filters treated as "must match"
principals: [
    {"filter": "Sales Team", "exception": 0},
    {"filter": "Managers", "exception": 0}
]
# This means: (Sales Team OR Managers) - correct if that's what you want

# RIGHT - Exception filter
principals: [
    {"filter": "All Employees", "exception": 0},
    {"filter": "Suspended", "exception": 1}
]
# This means: All Employees EXCEPT Suspended
```

### 2. Not Handling "All Records" Case

```python
# WRONG - Empty resources means different things
rule.resources = []  # This means "all records" - not "no records"

# RIGHT - Explicit "all records"
# Leave resources empty, system automatically adds {"all": 1}
```

### 3. Mixing Reference DocTypes

```python
# WRONG - Resource filter for wrong doctype
resource_filter = {
    "filter_name": "My Filter",
    "reference_doctype": "Sales Order",  # Wrong!
    "filters": [["customer", "=", "CUST-001"]]
}

rule = {
    "resource": "Customer",  # Resource is Customer
    "resources": [{"filter": resource_filter.name}]  # But filter is for Sales Order!
}
# This will fail validation

# RIGHT - Matching reference doctype
resource_filter = {
    "filter_name": "My Filter",
    "reference_doctype": "Customer",  # Matches resource
    "filters": [["customer_name", "like", "%Test%"]]
}
```

### 4. Permit vs Forbid Confusion

```python
# User will have access if:
# - At least ONE Permit rule matches
# - AND ZERO Forbid rules match

# So this is pointless:
Permit Rule 1: All records
Forbid Rule 2: Archived records
# User CANNOT access archived records even though Permit allows all

# Better approach:
Permit Rule 1: Active records (with filter)
# No Forbid rule needed
```

### 5. SQL Injection in Python Filters

```python
# WRONG - Vulnerable to SQL injection
user_input = "'; DROP TABLE Customer; --"
conditions = f"owner = '{user_input}'"  # DANGEROUS!

# RIGHT - Always escape
user_input = "'; DROP TABLE Customer; --"
conditions = f"owner = {frappe.db.escape(user_input)}"  # Safe
```

## Related Documentation

- Main Instructions: `.github/copilot-instructions.md`
- Sync Job Framework: `.github/instructions/sync-job.instructions.md`
- OpenObserve API: `.github/instructions/open-observe-api.instructions.md`
- Instructions Guidelines: `.github/instructions/instructions.instructions.md`
- TODO Tracking: `docs/todo/README.md`

## Conclusion

The AC Rule and Query Filter system provides a powerful, flexible framework for implementing fine-grained access control in Frappe applications.

**Current Capabilities**:
- ✅ Fully functional for Reports (with manual integration)
- ✅ Complete API for permission queries
- ✅ Flexible filter system (JSON, SQL, Python)
- ✅ DocType integration complete (automatic enforcement)

**Key Takeaways**:
- Use Query Filters for reusable, flexible filtering
- Understand the Permit/Forbid rule logic
- Always escape user input in SQL filters
- For Reports: Manually call `get_resource_filter_query()` and inject SQL
- For DocTypes: Automatic enforcement via permission query condition hooks (no manual integration needed)
- Migrate from deprecated systems (Event Scripts, Server Script Permission Policy)
- Test rules thoroughly before deployment
- Monitor performance with complex rule sets
- Follow the established code patterns and conventions
