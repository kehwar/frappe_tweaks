# Troubleshooting AC Rules

Common issues and debugging techniques for AC Rules.

## Rules Not Applying

### Symptoms
- User can see records they shouldn't be able to see
- User cannot see records they should be able to see
- Rules don't seem to take effect

### Check List

1. **Rule is enabled**
   ```python
   rule = frappe.get_doc("AC Rule", "your-rule-name")
   print(f"Disabled: {rule.disabled}")  # Should be 0
   ```

2. **Rule is within valid date range**
   ```python
   from datetime import datetime
   now = datetime.now()
   print(f"Valid from: {rule.valid_from}")
   print(f"Valid upto: {rule.valid_upto}")
   print(f"Current: {now}")
   ```

3. **Resource is not disabled**
   ```python
   resource = frappe.get_doc("AC Resource", rule.resource)
   print(f"Resource disabled: {resource.disabled}")  # Should be 0
   ```

4. **Actions are properly configured**
   ```python
   print(f"Managed actions: {resource.managed_actions}")
   print(f"Actions: {[a.action for a in resource.actions]}")
   ```

5. **User matches at least one principal filter**
   ```python
   from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_rules
   
   result = get_resource_rules(
       doctype="Customer",
       action="read",
       user="test@example.com"
   )
   print(f"Matching rules: {len(result.get('rules', []))}")
   ```

6. **Rule map is up to date**
   - Clear cache: `frappe.cache().delete_value("ac_rule_map")`
   - Restart server to ensure latest rules are loaded

## Incorrect Filtering

### Symptoms
- Wrong records are shown/hidden
- Filter logic seems inverted
- All records blocked when some should be accessible

### Debugging Steps

1. **Preview Query Filter SQL**
   ```python
   qf = frappe.get_doc("Query Filter", "your-filter-name")
   sql = qf.get_sql()
   print(f"Generated SQL: {sql}")
   ```

2. **Test SQL directly**
   ```python
   # For principal filters
   users = frappe.db.sql(f"""
       SELECT name FROM `tabUser`
       WHERE {sql}
   """, as_dict=True)
   print(f"Matching users: {[u.name for u in users]}")
   
   # For resource filters
   records = frappe.db.sql(f"""
       SELECT name FROM `tabCustomer`
       WHERE {sql}
   """, as_dict=True)
   print(f"Matching records: {[r.name for r in records]}")
   ```

3. **Check filter reference doctype**
   ```python
   qf = frappe.get_doc("Query Filter", "your-filter-name")
   print(f"Reference doctype: {qf.reference_doctype}")
   
   # Should match the resource's doctype
   resource = frappe.get_doc("AC Resource", rule.resource)
   if resource.type == "DocType":
       print(f"Resource doctype: {resource.document_type}")
       assert qf.reference_doctype == resource.document_type
   ```

4. **Verify filter type is appropriate**
   ```python
   print(f"Filter type: {qf.filters_type}")
   
   # JSON - Simple filters
   # SQL - Complex conditions
   # Python - Dynamic filters
   ```

5. **Check exception flag**
   ```python
   for p in rule.principals:
       print(f"Principal: {p.filter}, Exception: {p.exception}")
   
   for r in rule.resources:
       print(f"Resource: {r.filter}, Exception: {r.exception}")
   ```

6. **Test final query**
   ```python
   from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query
   
   result = get_resource_filter_query(
       doctype="Customer",
       action="read"
   )
   
   print(f"Access level: {result.get('access')}")
   print(f"Query: {result.get('query')}")
   ```

## Performance Problems

### Symptoms
- Slow list views
- Timeout errors
- High database CPU usage
- Queries taking too long

### Analysis Steps

1. **Check number of rules**
   ```python
   from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_rule_map
   
   rule_map = get_rule_map()
   doctype_rules = rule_map.get("doctype", {}).get("Customer", {}).get("", {})
   
   for action, rules in doctype_rules.items():
       print(f"Action {action}: {len(rules)} rules")
   ```

2. **Analyze generated SQL**
   ```python
   from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query
   
   result = get_resource_filter_query(
       doctype="Customer",
       action="read"
   )
   
   query = result.get("query")
   print(f"Query complexity: {len(query)} characters")
   print(f"Query: {query}")
   ```

3. **Test query performance**
   ```python
   import time
   
   start = time.time()
   data = frappe.db.sql(f"""
       SELECT name FROM `tabCustomer`
       WHERE {query}
   """)
   duration = time.time() - start
   
   print(f"Query took {duration:.2f} seconds")
   print(f"Returned {len(data)} records")
   ```

4. **Use EXPLAIN to analyze**
   ```python
   explain = frappe.db.sql(f"""
       EXPLAIN
       SELECT name FROM `tabCustomer`
       WHERE {query}
   """, as_dict=True)
   
   for row in explain:
       print(row)
   ```

### Solutions

1. **Consolidate similar rules**
   - Combine multiple rules with similar logic
   - Use fewer, more comprehensive filters

2. **Add database indexes**
   ```python
   # Add index to frequently filtered fields
   frappe.db.sql("""
       ALTER TABLE `tabCustomer`
       ADD INDEX idx_status (status)
   """)
   ```

3. **Convert Python filters to SQL**
   - Python filters require execution overhead
   - SQL filters are more efficient

4. **Implement rule map caching**
   ```python
   @frappe.cache()
   def get_rule_map():
       # Expensive operation - cache this
       pass
   ```

5. **Use specific queues for heavy operations**
   - Keep complex filters in separate resources
   - Consider denormalizing data if needed

## Access Denied When Should Allow

### Symptoms
- User should have access but gets "No permission" error
- Permit rule exists but doesn't work

### Debugging Steps

1. **Check for Forbid rules**
   ```python
   from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_rules
   
   result = get_resource_rules(
       doctype="Customer",
       action="read",
       user="test@example.com"
   )
   
   for rule in result.get("rules", []):
       print(f"Rule: {rule.get('title')}, Type: {rule.get('type')}")
   ```
   
   **Remember**: Forbid rules take precedence over Permit rules

2. **Verify user matches principals**
   ```python
   # Test if user matches principal filter
   qf = frappe.get_doc("Query Filter", "Sales Team")
   sql = qf.get_sql()
   
   users = frappe.db.sql(f"""
       SELECT name FROM `tabUser`
       WHERE {sql}
       AND name = 'test@example.com'
   """)
   
   print(f"User matches: {len(users) > 0}")
   ```

3. **Verify record matches resources**
   ```python
   # Test if record matches resource filter
   qf = frappe.get_doc("Query Filter", "Active Customers")
   sql = qf.get_sql()
   
   records = frappe.db.sql(f"""
       SELECT name FROM `tabCustomer`
       WHERE {sql}
       AND name = 'CUST-001'
   """)
   
   print(f"Record matches: {len(records) > 0}")
   ```

4. **Check Frappe's built-in permissions**
   ```python
   # AC Rules work alongside Frappe permissions
   has_perm = frappe.has_permission("Customer", "read", user="test@example.com")
   print(f"Frappe permission: {has_perm}")
   ```

5. **Test with Administrator**
   ```python
   # Administrator always has access
   result = get_resource_filter_query(
       doctype="Customer",
       action="read",
       user="Administrator"
   )
   print(f"Admin access: {result.get('access')}")  # Should be 'total'
   ```

## Common Mistakes

### 1. Mixing Reference DocTypes

**Problem**:
```python
# Resource filter for wrong doctype
resource_filter = {
    "filter_name": "My Filter",
    "reference_doctype": "Sales Order",  # Wrong!
    "filters": [["customer", "=", "CUST-001"]]
}

rule = {
    "resource": "Customer",  # Resource is Customer
    "resources": [{"filter": resource_filter.name}]
}
```

**Solution**: Match reference doctype to resource
```python
resource_filter = {
    "filter_name": "My Filter",
    "reference_doctype": "Customer",  # Correct
    "filters": [["customer_name", "like", "%Test%"]]
}
```

### 2. Forgetting Exception Logic

**Problem**:
```python
# Both filters treated as "must match"
principals: [
    {"filter": "Sales Team", "exception": 0},
    {"filter": "Managers", "exception": 0}
]
# This means: (Sales Team OR Managers)
```

**Solution**: Use exception correctly
```python
principals: [
    {"filter": "All Employees", "exception": 0},
    {"filter": "Suspended", "exception": 1}
]
# This means: All Employees EXCEPT Suspended
```

### 3. SQL Injection in Python Filters

**Problem**:
```python
# Vulnerable to SQL injection
conditions = f"owner = '{user}'"  # DANGEROUS!
```

**Solution**: Always escape
```python
# Safe
conditions = f"owner = {frappe.db.escape(user)}"
```

### 4. Empty Resources Confusion

**Problem**: Assuming empty resources means "no access"

**Fact**: Empty resources means "ALL records"

**Solution**: 
- Leave resources empty for all-record access
- Add specific filters to restrict access

### 5. Permit vs Forbid Confusion

**Problem**:
```python
# Pointless combination
Permit Rule 1: All records (1=1)
Forbid Rule 2: Archived records (status = 'Archived')
# User CANNOT access archived even though Permit allows all
```

**Solution**: Use single Permit with filter
```python
Permit Rule 1: Active records (status = 'Active')
# No Forbid rule needed
```

## Debugging Tools

### 1. Enable Verbose Logging

```python
import frappe
frappe.flags.debug = True
```

### 2. Check Rule Resolution

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_rules

result = get_resource_rules(
    doctype="Customer",
    action="read",
    user="test@example.com"
)

print(frappe.as_json(result, indent=2))
```

### 3. Test Filter Generation

```python
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import (
    get_principal_filter_sql,
    get_resource_filter_sql
)

# Test principal filter
filter_doc = frappe.get_doc("Query Filter", "Sales Team")
sql = get_principal_filter_sql({"name": filter_doc.name})
print(f"Principal SQL: {sql}")

# Test resource filter
sql = get_resource_filter_sql({"name": filter_doc.name})
print(f"Resource SQL: {sql}")
```

### 4. Monitor Cache

```python
# Check if rule map is cached
cached = frappe.cache().get_value("ac_rule_map")
print(f"Rule map cached: {cached is not None}")

# Clear cache
frappe.cache().delete_value("ac_rule_map")
```

### 5. Trace SQL Queries

```python
# Enable SQL logging
frappe.flags.log_sql = True

# Perform operation
customers = frappe.get_all("Customer")

# Check logged queries
print(frappe.db.sql_list)
```

## Getting Help

If you're still stuck after trying these debugging steps:

1. **Check the logs**: Look in Frappe Error Log for detailed error messages
2. **Test in isolation**: Create a simple test case with minimal rules
3. **Verify prerequisites**: Ensure all components (Rule, Resource, Filters) are properly configured
4. **Check documentation**: Review the integration and core components documentation
5. **Ask for help**: Provide error messages, rule configuration, and what you've tried
