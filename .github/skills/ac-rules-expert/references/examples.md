# Usage Examples and Patterns

Complete examples demonstrating common AC Rule patterns and use cases.

## Example 1: Sales Team Access Control (Report)

**Goal**: Create a Sales Report that only shows customers managed by the current user.

### Step 1: Create Query Filter for Sales Team Users

```python
# Via UI or code
sales_team_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Sales Team Members",
    "reference_doctype": "User",
    "filters_type": "JSON",
    "filters": frappe.as_json([["email", "like", "%@sales.company.com"]])
}).insert()
```

### Step 2: Create Query Filter for Managed Customers

```python
managed_customers_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "My Managed Customers",
    "reference_doctype": "Customer",
    "filters_type": "Python",
    "filters": """
conditions = f"`tabCustomer`.`account_manager` = {frappe.db.escape(frappe.session.user)}"
"""
}).insert()
```

### Step 3: Create AC Resource

```python
resource = frappe.get_doc({
    "doctype": "AC Resource",
    "type": "Report",
    "report": "Sales Customer Report",
    "managed_actions": "Select",
    "actions": [{"action": "Read"}]
}).insert()
```

### Step 4: Create AC Rule

```python
rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Sales Team Read Managed Customers",
    "type": "Permit",
    "resource": resource.name,
    "actions": [{"action": "Read"}],
    "principals": [
        {"filter": sales_team_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": managed_customers_filter.name, "exception": 0}
    ]
}).insert()
```

### Step 5: Integrate in Report Code

```python
# In your report's execute() function
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

def execute(filters=None):
    columns = get_columns()
    
    # Get AC Rule filter
    result = get_resource_filter_query(
        report="Sales Customer Report",
        action="read"
    )
    
    if result.get("access") == "none":
        return columns, []
    
    ac_filter = result.get("query", "1=1")
    
    # Use the filter in your query
    data = frappe.db.sql(f"""
        SELECT 
            name,
            customer_name,
            account_manager,
            status
        FROM `tabCustomer`
        WHERE {ac_filter}
        ORDER BY name
    """, as_dict=True)
    
    return columns, data
```

## Example 2: Restrict Archived Records (DocType)

**Goal**: Prevent all users (except Administrator) from reading archived customer records.

### Step 1: Create Query Filter for Archived Records

```python
archived_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Archived Customers",
    "reference_doctype": "Customer",
    "filters_type": "JSON",
    "filters": frappe.as_json([["status", "=", "Archived"]])
}).insert()
```

### Step 2: Create Query Filter for All Users

```python
all_users_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "All Users",
    "reference_doctype": "Role",
    "filters_type": "JSON",
    "filters": frappe.as_json([["name", "=", "All"]])
}).insert()
```

### Step 3: Create AC Resource

```python
resource = frappe.get_doc({
    "doctype": "AC Resource",
    "type": "DocType",
    "document_type": "Customer",
    "managed_actions": "Select",
    "actions": [{"action": "Read"}]
}).insert()
```

### Step 4: Create Forbid AC Rule

```python
rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Forbid Archived Customer Access",
    "type": "Forbid",
    "resource": resource.name,
    "actions": [{"action": "Read"}],
    "principals": [
        {"filter": all_users_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": archived_filter.name, "exception": 0}
    ]
}).insert()
```

**Note**: No code integration needed for DocTypes - this rule is automatically enforced!

## Example 3: Tenant-Based Multi-Tenancy

**Goal**: Multi-tenant setup where users only see their tenant's data.

### Step 1: Create Query Filter for Tenant Users

```python
tenant_users_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Tenant Users",
    "reference_doctype": "User",
    "filters_type": "Python",
    "filters": """
tenant_id = frappe.db.get_value("User", frappe.session.user, "tenant_id")
conditions = f"`tabUser`.`tenant_id` = {tenant_id}"
"""
}).insert()
```

### Step 2: Create Query Filter for Tenant Records

```python
tenant_orders_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Tenant Sales Orders",
    "reference_doctype": "Sales Order",
    "filters_type": "Python",
    "filters": """
tenant_id = frappe.db.get_value("User", frappe.session.user, "tenant_id")
conditions = f"`tabSales Order`.`tenant_id` = {tenant_id}"
"""
}).insert()
```

### Step 3: Create AC Resource

```python
resource = frappe.get_doc({
    "doctype": "AC Resource",
    "type": "DocType",
    "document_type": "Sales Order",
    "managed_actions": "All Actions"
}).insert()
```

### Step 4: Create Permit AC Rule

```python
rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Tenant Data Isolation",
    "type": "Permit",
    "resource": resource.name,
    "actions": [
        {"action": "Read"},
        {"action": "Write"},
        {"action": "Create"},
        {"action": "Delete"}
    ],
    "principals": [
        {"filter": tenant_users_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": tenant_orders_filter.name, "exception": 0}
    ]
}).insert()
```

## Example 4: Department-Based Access with Exceptions

**Goal**: Allow department members to access their department's documents, except suspended users.

### Step 1: Create Principal Filters

```python
# Department members
dept_users_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Department Users",
    "reference_doctype": "User",
    "filters_type": "Python",
    "filters": """
user_dept = frappe.db.get_value("User", frappe.session.user, "department")
conditions = f"`tabUser`.`department` = {frappe.db.escape(user_dept)}"
"""
}).insert()

# Suspended users (exception)
suspended_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Suspended Users",
    "reference_doctype": "User",
    "filters_type": "JSON",
    "filters": frappe.as_json([["enabled", "=", 0]])
}).insert()
```

### Step 2: Create Resource Filters

```python
# Department documents
dept_docs_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Department Projects",
    "reference_doctype": "Project",
    "filters_type": "Python",
    "filters": """
user_dept = frappe.db.get_value("User", frappe.session.user, "department")
conditions = f"`tabProject`.`department` = {frappe.db.escape(user_dept)}"
"""
}).insert()
```

### Step 3: Create AC Rule with Exceptions

```python
resource = frappe.get_doc({
    "doctype": "AC Resource",
    "type": "DocType",
    "document_type": "Project",
    "managed_actions": "Select",
    "actions": [{"action": "Read"}, {"action": "Write"}]
}).insert()

rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Department Access (Exclude Suspended)",
    "type": "Permit",
    "resource": resource.name,
    "actions": [{"action": "Read"}, {"action": "Write"}],
    "principals": [
        {"filter": dept_users_filter.name, "exception": 0},  # Include dept users
        {"filter": suspended_filter.name, "exception": 1}    # Exclude suspended
    ],
    "resources": [
        {"filter": dept_docs_filter.name, "exception": 0}
    ]
}).insert()
```

## Example 5: Complex SQL Filter with Subqueries

**Goal**: Allow users to access customers based on their user permissions.

### Step 1: Create Resource Filter with Subquery

```python
permitted_customers_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Permitted Customers",
    "reference_doctype": "Customer",
    "filters_type": "SQL",
    "filters": """
customer_type IN (
    SELECT allowed_type 
    FROM `tabUser Permissions` 
    WHERE parent = '{user}'
    AND doctype = 'Customer Type'
) 
AND status != 'Cancelled'
"""
}).insert()
```

### Step 2: Create AC Rule

```python
resource = frappe.get_doc({
    "doctype": "AC Resource",
    "type": "DocType",
    "document_type": "Customer",
    "managed_actions": "All Actions"
}).insert()

all_users_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "All Users",
    "reference_doctype": "Role",
    "filters_type": "JSON",
    "filters": frappe.as_json([["name", "=", "All"]])
}).insert()

rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "User Permission Based Access",
    "type": "Permit",
    "resource": resource.name,
    "actions": [
        {"action": "Read"},
        {"action": "Write"}
    ],
    "principals": [
        {"filter": all_users_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": permitted_customers_filter.name, "exception": 0}
    ]
}).insert()
```

## Example 6: Combining Multiple Permit Rules

**Goal**: Allow both managers and team leaders to access team documents.

### Step 1: Create Principal Filters

```python
managers_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Managers",
    "reference_doctype": "Role",
    "filters_type": "JSON",
    "filters": frappe.as_json([["name", "=", "Manager"]])
}).insert()

team_leaders_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Team Leaders",
    "reference_doctype": "Role",
    "filters_type": "JSON",
    "filters": frappe.as_json([["name", "=", "Team Leader"]])
}).insert()
```

### Step 2: Create Resource Filter

```python
active_tasks_filter = frappe.get_doc({
    "doctype": "Query Filter",
    "filter_name": "Active Tasks",
    "reference_doctype": "Task",
    "filters_type": "JSON",
    "filters": frappe.as_json([["status", "!=", "Completed"]])
}).insert()
```

### Step 3: Create Two Permit Rules

```python
resource = frappe.get_doc({
    "doctype": "AC Resource",
    "type": "DocType",
    "document_type": "Task",
    "managed_actions": "Select",
    "actions": [{"action": "Read"}, {"action": "Write"}]
}).insert()

# Rule 1: Managers
manager_rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Managers Access Tasks",
    "type": "Permit",
    "resource": resource.name,
    "actions": [{"action": "Read"}, {"action": "Write"}],
    "principals": [
        {"filter": managers_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": active_tasks_filter.name, "exception": 0}
    ]
}).insert()

# Rule 2: Team Leaders
leader_rule = frappe.get_doc({
    "doctype": "AC Rule",
    "title": "Team Leaders Access Tasks",
    "type": "Permit",
    "resource": resource.name,
    "actions": [{"action": "Read"}, {"action": "Write"}],
    "principals": [
        {"filter": team_leaders_filter.name, "exception": 0}
    ],
    "resources": [
        {"filter": active_tasks_filter.name, "exception": 0}
    ]
}).insert()
```

**Result**: Users with either Manager OR Team Leader role can access active tasks.

## Common Patterns Summary

### 1. User-Based Filtering

```python
filters = """
user = frappe.session.user
conditions = f"`tabDocType`.`owner` = {frappe.db.escape(user)}"
"""
```

### 2. Role-Based Filtering

```python
# JSON filter for Role
filters = frappe.as_json([["name", "in", ["Sales User", "Sales Manager"]]])
```

### 3. Dynamic Field-Based Filtering (using conditions)

```python
# Python filter - using conditions variable
filters = """
user_value = frappe.db.get_value("User", frappe.session.user, "custom_field")
conditions = f"`tabDocType`.`field` = {frappe.db.escape(user_value)}"
"""
```

### 3b. Dynamic Field-Based Filtering (using filters)

```python
# Python filter - using filters variable (like JSON)
filters = """
user_value = frappe.db.get_value("User", frappe.session.user, "custom_field")
filters = [["field", "=", user_value]]
"""
# This is converted to SQL just like JSON filters
```

### 4. Time-Based Filtering

```python
filters = frappe.as_json([
    ["creation", ">=", "2024-01-01"],
    ["creation", "<=", "2024-12-31"]
])
```

### 5. Status-Based Filtering

```python
filters = frappe.as_json([
    ["status", "in", ["Draft", "Pending", "Approved"]]
])
```

### 6. Hierarchical Filtering (using conditions)

```python
# Python filter - using conditions variable for complex SQL
filters = """
conditions = f'''EXISTS (
    SELECT 1 FROM `tabEmployee`
    WHERE reports_to = {frappe.db.escape(frappe.session.user)}
    AND name = `tabDocType`.`employee`
)'''
"""
```

### 7. Python Filter with Fallback

```python
# Python filter - try conditions first, fallback to filters
filters = """
# Try to build complex SQL condition
try:
    user_dept = frappe.db.get_value("User", frappe.session.user, "department")
    if user_dept:
        conditions = f"`tabDocType`.`department` = {frappe.db.escape(user_dept)}"
    else:
        # Fallback to filters dict
        filters = [["department", "is", "set"]]
except:
    # Error case - block all
    conditions = "1=0"
"""
```
