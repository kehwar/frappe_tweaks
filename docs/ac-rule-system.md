# AC Rule System Documentation

## Overview

The AC (Access Control) Rule System is an advanced, rule-based access control framework for Frappe applications. It extends Frappe's built-in role-based permissions with fine-grained, record-level access control.

## Table of Contents

- [Introduction](#introduction)
- [Key Concepts](#key-concepts)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

### What is the AC Rule System?

The AC Rule System provides:

- **Fine-grained access control**: Control access at the record level, not just doctype level
- **Rule-based logic**: Define complex access rules with Permit/Forbid semantics
- **Dynamic filtering**: Use SQL, Python, or JSON filters to determine access
- **Principal-based**: Define who has access (users, roles, user groups)
- **Resource-based**: Define what is being accessed (doctypes, reports)
- **Action-based**: Control specific actions (read, write, delete, etc.)

### When to Use AC Rules?

Use AC Rules when you need:

- Record-level permissions based on field values
- Multi-tenant data isolation
- Territory/region-based access control
- Dynamic permissions based on user attributes
- Complex business logic for access control

**Note**: AC Rules complement Frappe's built-in permissions, they don't replace them.

## Key Concepts

### 1. AC Rule

The central component that defines an access control rule.

**Components**:
- **Type**: Either "Permit" (grant access) or "Forbid" (deny access)
- **Resource**: What is being accessed (e.g., Customer doctype)
- **Actions**: Which operations are controlled (e.g., read, write)
- **Principal Filters**: Who the rule applies to (user filtering)
- **Resource Filters**: Which records the rule applies to (record filtering)

**Logic**:
```
Access granted if:
  (At least one Permit rule matches) 
  AND 
  (No Forbid rules match)
```

### 2. Query Filter

Reusable filter definitions used for both principal and resource filtering.

**Filter Types**:
- **JSON**: Standard Frappe filter syntax `[["field", "operator", "value"]]`
- **SQL**: Direct SQL WHERE clause `field = 'value' AND other_field > 10`
- **Python**: Python code that sets `conditions` variable

**Common Use Cases**:
- Filter users by department, role, or custom criteria
- Filter records by status, owner, region, or any field
- Complex filtering with subqueries or joins

### 3. AC Resource

Defines the resource being protected (what is being accessed).

**Resource Types**:
- **DocType**: A Frappe DocType (e.g., "Customer", "Sales Order")
- **Report**: A Frappe Report

**Managed Actions**:
- Specify which actions this resource manages (read, write, etc.)
- Choose between "All Actions" or "Select" specific actions

### 4. AC Action

Standard actions that can be controlled:
- Read
- Write
- Create
- Delete
- Submit
- Cancel
- Export
- Print
- Email
- Share
- (Custom actions can be added)

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                      AC Rule System                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐    │
│  │ AC Rule  │─────▶│   Query  │◀─────│   AC     │    │
│  │          │      │  Filter  │      │ Resource │    │
│  └──────────┘      └──────────┘      └──────────┘    │
│       │                  │                   │         │
│       │                  │                   │         │
│       ▼                  ▼                   ▼         │
│  ┌──────────────────────────────────────────────┐    │
│  │          Rule Map (Cached)                   │    │
│  └──────────────────────────────────────────────┘    │
│                        │                              │
│                        ▼                              │
│  ┌──────────────────────────────────────────────┐    │
│  │     Permission Evaluation Engine             │    │
│  └──────────────────────────────────────────────┘    │
│                        │                              │
└────────────────────────┼──────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ Frappe Permissions   │
              │      System          │
              └──────────────────────┘
```

### Evaluation Flow

1. **Request**: User tries to access a resource
2. **Rule Lookup**: System finds applicable rules for resource/action
3. **Principal Filtering**: Check if user matches principal filters
4. **Resource Filtering**: Generate SQL to filter accessible records
5. **Access Decision**: 
   - If Forbid rule matches → Access Denied
   - If Permit rule matches → Access Granted (with filters)
   - If no rules → Unmanaged (fall back to Frappe permissions)

### SQL Generation

The system generates SQL WHERE clauses for filtering:

```sql
-- Principal Filtering (WHO has access)
SELECT rule FROM (
  SELECT 'Rule1' AS rule FROM `tabUser` 
  WHERE `tabUser`.`name` = 'john@example.com' 
    AND (department = 'Sales')
  UNION
  SELECT 'Rule2' AS rule FROM `tabUser` 
  WHERE `tabUser`.`name` = 'john@example.com' 
    AND (`tabUser`.`name` IN (SELECT user FROM ...))
)

-- Resource Filtering (WHAT they can access)
-- Combined from all matching Permit rules
(status = 'Active' AND region = 'North')
OR (owner = 'john@example.com')
AND NOT (status = 'Archived')  -- Forbid rules
```

## Getting Started

### Step 1: Create a Query Filter

**For Principal Filtering** (who has access):

Navigate to: **Query Filter > New**

```
Filter Name: Sales Team Members
Reference Doctype: User
Filters Type: JSON
Filters: [["department", "=", "Sales"]]
```

**For Resource Filtering** (what they can access):

```
Filter Name: Active Customers
Reference Doctype: Customer
Filters Type: JSON
Filters: [["status", "=", "Active"]]
```

### Step 2: Create or Configure AC Resource

Navigate to: **AC Resource > New**

```
Type: DocType
Document Type: Customer
Managed Actions: Select
Actions: 
  - Read
  - Write
```

### Step 3: Create AC Rule

Navigate to: **AC Rule > New**

```
Title: Sales Team Active Customer Access
Type: Permit
Resource: Customer
Actions:
  - Read
  - Write
Principal Filters:
  - Filter: Sales Team Members, Exception: No
Resource Filters:
  - Filter: Active Customers, Exception: No
```

### Step 4: Test Access

```python
# In Python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access

result = has_resource_access(
    doctype="Customer",
    action="read",
    user="john@example.com"
)

print(result.get("access"))  # True or False
```

```javascript
// In JavaScript
frappe.call({
    method: 'tweaks.tweaks.doctype.ac_rule.ac_rule_utils.has_resource_access',
    args: {
        doctype: 'Customer',
        action: 'read',
        user: 'john@example.com'
    },
    callback: function(r) {
        console.log(r.message.access);  // true or false
    }
});
```

## API Reference

### Python API

#### get_rule_map(debug=False)

Get the complete rule map structure.

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_rule_map

rule_map = get_rule_map(debug=True)
```

**Returns**: Dictionary organized by resource type, name, fieldname, and action.

#### get_resource_rules(doctype, action, user, ...)

Get all rules that apply to a specific resource/action for a user.

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_rules

result = get_resource_rules(
    doctype="Customer",
    action="read",
    user="john@example.com",
    debug=True
)

print(result.get("rules"))  # List of matching rules
print(result.get("unmanaged"))  # True if resource not managed
```

**Parameters**:
- `resource` (str): AC Resource name
- `doctype` (str): DocType name
- `report` (str): Report name
- `action` (str): Action name (default: "read")
- `user` (str): User email (default: current user)
- `debug` (bool): Include debug information

**Returns**: Dictionary with `rules` and `unmanaged` keys.

#### get_resource_filter_query(doctype, action, user, ...)

Get the SQL WHERE clause for filtering accessible records.

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

result = get_resource_filter_query(
    doctype="Customer",
    action="read",
    user="john@example.com"
)

print(result.get("query"))  # SQL WHERE clause
print(result.get("access"))  # "total", "partial", "none", or "unmanaged"
```

**Returns**: Dictionary with `query` and `access` keys.

**Access Levels**:
- `total`: User has access to all records
- `partial`: User has access to some records (filter applied)
- `none`: User has no access
- `unmanaged`: Resource not managed by AC Rules

#### has_resource_access(doctype, action, user, ...)

Check if user has any access to a resource/action.

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access

result = has_resource_access(
    doctype="Customer",
    action="write",
    user="john@example.com"
)

if result.get("access"):
    print("User has write access")
else:
    print("User does not have write access")
```

**Returns**: Dictionary with `access` boolean.

### JavaScript API

All Python APIs are whitelisted and can be called from JavaScript:

```javascript
frappe.call({
    method: 'tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_resource_filter_query',
    args: {
        doctype: 'Customer',
        action: 'read',
        user: frappe.session.user
    },
    callback: function(r) {
        console.log('SQL Query:', r.message.query);
        console.log('Access Level:', r.message.access);
    }
});
```

## Examples

For detailed examples including multi-tenant SaaS, hierarchical access, department-based filtering, and more, please refer to the comprehensive instructions file at `.github/instructions/ac-rule.instructions.md`.

### Quick Example: Department-Based Access

**Scenario**: Users can only access records from their own department.

1. Create Query Filter for User's Department:
   - Reference Doctype: User
   - Filters Type: Python
   - Filters: Dynamic lookup based on current user's department

2. Create Query Filter for Department Records:
   - Reference Doctype: Customer
   - Filters Type: Python
   - Filters: Match customer's department to user's department

3. Create AC Rule:
   - Type: Permit
   - Resource: Customer
   - Actions: Read, Write, Create
   - Link both filters

## Best Practices

1. **Design Reusable Filters**: Create generic filters that can be shared across multiple rules
2. **Use Clear Naming**: Name filters and rules descriptively
3. **Prefer JSON Filters**: Use JSON when possible for easier maintenance
4. **Test Thoroughly**: Always test filters with actual data before deploying
5. **Document Complex Rules**: Add clear descriptions for complex access logic
6. **Handle Edge Cases**: Consider what happens with NULL values or missing data
7. **Optimize Performance**: Add indexes, avoid complex subqueries, cache results
8. **Security First**: Always escape user input in SQL filters
9. **Organize Rules**: Group rules logically (general → specific → exceptions)
10. **Test Systematically**: Test with different user types and scenarios

For complete best practices, security considerations, and advanced topics, see `.github/instructions/ac-rule.instructions.md`.

## Troubleshooting

### Common Issues

1. **Rules Not Working**: Check if rule is enabled, within date range, and user matches principals
2. **Incorrect Filtering**: Verify filter SQL with Preview button, check reference doctype matches
3. **Performance Issues**: Add indexes, consolidate rules, optimize complex queries
4. **No Access**: Check for conflicting Forbid rules (they take precedence)
5. **SQL Errors**: Verify SQL syntax, table names, and field names

### Debug Mode

Use `debug=True` in API calls to get detailed information:

```python
result = get_resource_filter_query(
    doctype="Customer",
    action="read",
    user="test@example.com",
    debug=True
)

print("Query:", result.get("query"))
print("Parts:", result.get("parts"))
print("Access:", result.get("access"))
```

For detailed troubleshooting steps and solutions, see the full documentation in `.github/instructions/ac-rule.instructions.md`.

## Additional Resources

- **Comprehensive Instructions**: `.github/instructions/ac-rule.instructions.md`
- **Source Code**: `tweaks/tweaks/doctype/ac_rule/`
- **Query Filter Implementation**: `tweaks/tweaks/doctype/query_filter/`
- **Test Files**: Check doctype directories for test implementations
- **Main README**: `README.md`

## FAQ

**Q: Do AC Rules replace Frappe's built-in permissions?**  
A: No, AC Rules complement Frappe's permissions. Both systems must grant access.

**Q: What's the performance impact?**  
A: Impact depends on rule complexity. Use caching and indexes to optimize.

**Q: Can I use AC Rules for custom doctypes?**  
A: Yes, AC Rules work with any doctype, custom or standard.

**Q: What happens if no rules match?**  
A: The resource is "unmanaged" and Frappe's standard permissions apply.

**Q: How do I debug why a user can't access something?**  
A: Use the `debug=True` parameter in API calls to see detailed information.

## Contributing

When working with AC Rules:

1. Follow the 4-space indentation rule (defined in .editorconfig)
2. Use descriptive names for rules and filters
3. Add comments for complex logic
4. Test thoroughly before committing
5. Update documentation when adding features

---

**Version**: 1.0  
**Last Updated**: 2026-01-04  
**Maintained By**: Frappe Tweaks Project

For complete implementation details, code patterns, security considerations, and advanced usage, please refer to `.github/instructions/ac-rule.instructions.md`.
