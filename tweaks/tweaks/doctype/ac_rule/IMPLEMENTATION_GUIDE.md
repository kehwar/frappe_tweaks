# AC Rule DocType Integration - Implementation Guide

## Overview

This document describes the implementation of automatic DocType permission enforcement for AC Rules. The implementation adds Frappe permission hooks that automatically filter list views and check document permissions based on AC Rules.

## Architecture

### Components

1. **Permission Hooks** (registered in `hooks.py`)
   - `has_permission`: Checks if user has permission to access a specific document
   - `permission_query_conditions`: Returns SQL WHERE clause to filter list views

2. **AC Rule Utils Functions** (`ac_rule_utils.py`)
   - `ptype_to_action()`: Maps Frappe permission types to AC Action names
   - `get_permission_query_conditions()`: Implements the permission query conditions hook
   - `has_permission()`: Implements the has permission hook

3. **Existing AC Rule System**
   - `get_rule_map()`: Builds map of all AC Rules
   - `get_resource_rules()`: Gets rules for a specific resource/action/user
   - `get_resource_filter_query()`: Builds SQL WHERE clause from rules

## How It Works

### List View Filtering (permission_query_conditions)

When a user opens a list view, Frappe calls `get_permission_query_conditions()` with:
- `doctype`: The DocType being viewed
- `user`: The current user

The function:
1. Checks if user is Administrator (returns "" for full access)
2. Calls `get_resource_filter_query()` with action="read"
3. Returns SQL WHERE clause based on AC Rules
4. Returns "" for unmanaged resources (falls through to standard Frappe permissions)

Example flow:
```
User opens Customer list
→ Frappe calls get_permission_query_conditions("Customer", "user@example.com")
→ Function gets AC Rules for Customer with action="read" for this user
→ Returns SQL: "(`tabCustomer`.`account_manager` = 'user@example.com')"
→ Frappe appends to query: SELECT * FROM tabCustomer WHERE (AC Rule filter) AND (other conditions)
```

### Single Document Check (has_permission)

When a user accesses a specific document, Frappe calls `has_permission()` with:
- `doc`: The document object or dict
- `ptype`: Permission type (read, write, create, delete, etc.)
- `user`: The current user

The function:
1. Checks if user is Administrator (returns True for full access)
2. Maps ptype to AC Action name (e.g., "read" → "Read")
3. Calls `get_resource_rules()` to get applicable rules
4. Returns None for unmanaged resources (falls through to standard Frappe permissions)
5. If rules exist, checks if document matches resource filters
6. Returns True if allowed, False if denied

Example flow:
```
User opens Customer "CUST-001"
→ Frappe calls has_permission(doc, ptype="write", user="user@example.com")
→ Function maps "write" to "Write" action
→ Gets AC Rules for Customer with action="Write" for this user
→ Checks if CUST-001 matches resource filters in the rules
→ Returns True if matches, False otherwise
```

## Permission Type Mapping

Frappe uses lowercase permission types (ptype), while AC Actions use title case:

| Frappe ptype | AC Action |
|--------------|-----------|
| read         | Read      |
| write        | Write     |
| create       | Create    |
| delete       | Delete    |
| submit       | Submit    |
| cancel       | Cancel    |
| amend        | Amend     |
| print        | Print     |
| email        | Email     |
| import       | Import    |
| export       | Export    |
| share        | Share     |
| select       | Select    |
| report       | Report    |

The `ptype_to_action()` function handles this mapping by capitalizing the first letter.

## Integration with Existing Systems

The AC Rule hooks work alongside existing permission systems:

```python
# In hooks.py
has_permission = {
    "*": (
        event_script_hooks["has_permission"]["*"]           # Event Scripts (deprecated)
        + permission_hooks["has_permission"]["*"]           # Server Script Permission Policy (deprecated)
        + ["tweaks.tweaks.doctype.ac_rule.ac_rule_utils.has_permission"]  # AC Rules (new)
    )
}
```

All hooks are called in order. If any hook returns False, permission is denied. If all return True/None, permission is granted.

## Unmanaged Resources

Resources without AC Rules defined are considered "unmanaged":
- `get_permission_query_conditions()` returns empty string ""
- `has_permission()` returns None

This allows standard Frappe permissions to handle the resource as normal.

## Administrator Bypass

Administrator always has full access:
- `get_permission_query_conditions()` returns "" for Administrator
- `has_permission()` returns True for Administrator

This ensures Administrator can always access all records regardless of AC Rules.

## Performance Considerations

### List View Performance

The SQL WHERE clause is generated once per list view load and appended to the main query. This is efficient because:
1. Rule map is generated once (can be cached in future)
2. Principal filtering uses SQL subqueries
3. Resource filtering uses SQL conditions
4. Final query is executed by database engine

### Single Document Performance

Document permission check evaluates rules for each document access. For better performance:
1. Use simpler resource filters when possible
2. Avoid complex Python filters for frequently accessed documents
3. Consider caching rule evaluation results (future enhancement)

## Testing

### Unit Tests

Test file: `test_ac_rule_permissions.py`

Tests include:
- Permission type mapping
- Administrator access
- Unmanaged resource handling
- Hook registration
- Basic permission checks

### Static Verification

Verification script: `verify_static.py`

Checks:
- Function definitions
- Function logic patterns
- Hook registration
- Code structure

Run with:
```bash
python3 tweaks/tweaks/doctype/ac_rule/verify_static.py
```

## Migration from Deprecated Systems

### From Server Script Permission Policy

**Old approach:**
```python
# Server Script with permission_policy event
def get_permission_policy(user, ptype=None, doc=None):
    # Custom logic
    return {"allow": True, "query": "..."}
```

**New approach:**
1. Create Query Filters for principals and resources
2. Create AC Resource for the DocType
3. Create AC Rules with Permit/Forbid logic
4. No code needed - automatic enforcement

### From Event Scripts

**Old approach:**
```python
# Event Script for has_permission
if frappe.session.user in allowed_users:
    return True
return False
```

**New approach:**
1. Create Query Filter for allowed users
2. Create AC Resource for the DocType
3. Create AC Rule with Permit type
4. No code needed - automatic enforcement

## Example Usage

### Example 1: Sales Team Access

**Requirement**: Sales team members can only read/write customers they manage.

**Setup:**

1. Create Query Filter for Sales Team:
```
Name: Sales Team Members
Reference DocType: User
Type: JSON
Filters: [["department", "=", "Sales"]]
```

2. Create Query Filter for Managed Customers:
```
Name: My Managed Customers
Reference DocType: Customer
Type: Python
Filters:
conditions = f"`tabCustomer`.`account_manager` = {frappe.db.escape(frappe.session.user)}"
```

3. Create AC Resource:
```
Type: DocType
Document Type: Customer
Managed Actions: Select
Actions: Read, Write
```

4. Create AC Rule:
```
Title: Sales Team Customer Access
Type: Permit
Resource: Customer (AC Resource from step 3)
Actions: Read, Write
Principal Filters: Sales Team Members
Resource Filters: My Managed Customers
```

**Result**: Sales team members automatically see only their managed customers in list views and can only access their managed customers.

### Example 2: Restrict Archived Records

**Requirement**: Prevent all users from accessing archived customers.

**Setup:**

1. Create Query Filter for All Users:
```
Name: All Users
Reference DocType: Role
Type: JSON
Filters: [["name", "=", "All"]]
```

2. Create Query Filter for Archived:
```
Name: Archived Customers
Reference DocType: Customer
Type: JSON
Filters: [["status", "=", "Archived"]]
```

3. Create AC Resource (if not already created):
```
Type: DocType
Document Type: Customer
Managed Actions: Select
Actions: Read
```

4. Create AC Rule:
```
Title: Forbid Archived Customer Access
Type: Forbid
Resource: Customer
Actions: Read
Principal Filters: All Users
Resource Filters: Archived Customers
```

**Result**: No user can access archived customers, even if they would normally have access.

## Troubleshooting

### Issue: Rules not applying

**Check:**
1. AC Resource exists for the DocType
2. AC Resource has the correct actions enabled
3. AC Rule is enabled and within date range (valid_from/valid_upto)
4. User matches at least one principal filter
5. Resource filters reference the correct DocType

**Debug:**
```python
# In bench console
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query, get_resource_rules

# Check filter query
result = get_resource_filter_query(doctype="Customer", action="read", user="user@example.com", debug=True)
print(result)

# Check rules
rules = get_resource_rules(doctype="Customer", action="read", user="user@example.com", debug=True)
print(rules)
```

### Issue: Permission denied when should be allowed

**Check:**
1. No Forbid rule is overriding access (Forbid takes precedence over Permit)
2. User matches principal filters
3. Document matches resource filters
4. Standard Frappe permissions also allow access

### Issue: List view shows no records

**Check:**
1. Permission query conditions returning "1=0" (no access)
2. Resource filters too restrictive
3. Check debug output of get_resource_filter_query()

## Future Enhancements

1. **Rule Caching**: Cache rule map at site level for better performance
2. **Audit Logging**: Track when rules are evaluated and access granted/denied
3. **Rule Testing**: Built-in UI to test rules before deployment
4. **Performance Profiling**: Identify slow rules and suggest optimizations
5. **Visual Rule Builder**: UI for creating rules without writing code

## Summary

The AC Rule DocType integration provides automatic, rule-based permission enforcement for all DocTypes without requiring custom code. It seamlessly integrates with Frappe's permission system while providing fine-grained control over who can access what records.

Key benefits:
- ✅ Automatic enforcement (no manual integration required)
- ✅ Works alongside existing permission systems
- ✅ Flexible filter system (JSON, SQL, Python)
- ✅ Permit/Forbid rule logic
- ✅ Administrator bypass
- ✅ Unmanaged resource support
- ✅ Performance-optimized SQL generation
