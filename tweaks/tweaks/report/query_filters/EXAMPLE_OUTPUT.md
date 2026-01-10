# Query Filters Report - Example Output

This file shows what the report output might look like when run in a Frappe environment.

## Example 1: Basic Report (No Impersonation)

```
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
| Name              | Filter Name               | Reference DocType | Reference Report | Reference Document  | Type         | Disabled | Calculated SQL                                         |
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
| qf-001            | Active Users              | User              |                  |                     | JSON         | 0        | `tabUser`.`name` IN (SELECT `name` FROM `tabUser`...) |
| qf-002            | Sales Team Members        | User              |                  |                     | Python       | 0        | `tabUser`.`department` = 'Sales'                       |
| qf-003            | Administrator Only        | User              |                  | Administrator        | JSON         | 0        | `tabUser`.`name` = 'Administrator'                     |
| qf-004            | High Value Customers      | Customer          |                  |                     | SQL          | 0        | status = 'Active' AND credit_limit > 100000           |
| qf-005            | My Territory              | Customer          |                  |                     | Python       | 0        | `tabCustomer`.`territory` = 'North'                    |
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
```

## Example 2: With Impersonation (User = "test@example.com")

```
Filter: Impersonate User = "test@example.com"

+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
| Name              | Filter Name               | Reference DocType | Reference Report | Reference Document  | Type         | Disabled | Calculated SQL                                         |
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
| qf-001            | Active Users              | User              |                  |                     | JSON         | 0        | `tabUser`.`name` IN (SELECT `name` FROM `tabUser`...) |
| qf-002            | Sales Team Members        | User              |                  |                     | Python       | 0        | `tabUser`.`department` = 'Sales'                       |
| qf-005            | My Territory              | Customer          |                  |                     | Python       | 0        | `tabCustomer`.`territory` = 'South'                    |
|                   |                           |                   |                  |                     |              |          | (Note: Different territory because running as test@..)|
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+

Note: The SQL for "My Territory" is different because the Python filter uses frappe.session.user,
which evaluates to "test@example.com" when impersonating.
```

## Example 3: With Errors

```
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
| Name              | Filter Name               | Reference DocType | Reference Report | Reference Document  | Type         | Disabled | Calculated SQL                                         |
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
| qf-006            | Invalid Filter            | Customer          |                  |                     | JSON         | 0        | ERROR: Reference Doctype is required when using...     |
| qf-007            | Broken Python             |                   |                  |                     | Python       | 0        | ERROR: NameError: name 'undefined_var' is not defined  |
| qf-008            | Bad SQL Syntax            | User              |                  |                     | SQL          | 0        | status = 'Active' AND INVALID SYNTAX                   |
|                   |                           |                   |                  |                     |              |          | (Note: SQL errors may not show until executed)        |
+-------------------+---------------------------+-------------------+------------------+---------------------+--------------+----------+--------------------------------------------------------+
```

## Report Features

### Sorting
- Primary sort: Filter Name (ascending)
- Secondary sort: Name (ascending)

### Filtering
The report can be filtered by:
- **Impersonate User**: Optional Link field to User doctype
  - When set, all SQL calculations are done in the context of that user
  - Useful for debugging user-specific filters

### Column Details

1. **Name**: Clickable link to the Query Filter document
2. **Filter Name**: Human-readable name for the filter
3. **Reference DocType**: The DocType this filter applies to (empty if using reference_report)
4. **Reference Report**: The Report this filter applies to (empty if using reference_doctype)
5. **Reference Document**: Specific document name (only set for single-record filters)
6. **Type**: One of: JSON, Python, or SQL
7. **Disabled**: Checkbox showing if the filter is disabled
8. **Calculated SQL**: The actual SQL WHERE clause generated by the filter

### Use Cases

1. **Debugging Filters**: Quickly see what SQL is generated by each filter
2. **Testing User Context**: Use impersonation to see how filters evaluate for different users
3. **Documentation**: Generate a list of all filters with their SQL for documentation
4. **Troubleshooting**: Identify broken or misconfigured filters by looking for ERROR messages
5. **Performance Analysis**: Review generated SQL to identify potentially slow queries

### Notes

- The report uses `frappe.get_all()` and `frappe.get_doc()` to fetch data
- Each filter's `get_sql()` method is called to calculate the SQL
- Errors during SQL calculation are caught and displayed with "ERROR:" prefix
- The impersonation feature uses `frappe.set_user()` to switch context
- Original user context is always restored via a finally block
