# AC Rules Report

## Overview

The AC Rules report provides a comprehensive matrix view of all access control rules in the system. It helps administrators understand at a glance which combinations of resources, resource filters, and principal filters grant which actions.

## Report Structure

### Rows
Each row represents a unique combination of:
- **Resource**: An AC Resource (DocType or Report)
- **Resource Filter**: A Query Filter that defines which specific records/instances the rule applies to, or "All" if the rule applies to all records

### Columns
Each column represents a unique combination of:
- **Principal Filter**: A Query Filter that defines which users/roles the rule applies to
- **Exception Filters**: Any exception filters are shown with a ⚠️ emoji

### Cells
Each cell shows the aggregated actions that are granted for the intersection of:
- The row's (resource, resource filter) combination
- The column's (principal filter) combination

## Filters

### Action Filter (Optional)
When an action filter is specified, the report changes from showing a list of actions to showing:
- **Y**: The action is granted for this combination
- **N**: The action is not granted for this combination

This makes it easier to audit specific actions across all rules.

## Use Cases

### 1. Comprehensive Access Audit
View all access control rules in one place to understand the complete access control landscape.

### 2. Action-Specific Auditing
Filter by a specific action (e.g., "Read", "Write", "Delete") to see which resource/filter combinations grant that action to which principal/filter combinations.

### 3. Gap Analysis
Identify resources or resource filters that have no access rules configured (empty rows).

### 4. Over-Permission Detection
Identify principal filters that have access to many resource/filter combinations.

## How It Works

The report:
1. Loads all enabled AC Rules that are within their valid date range
2. Uses the `get_distinct_principal_query_filters()` method to extract unique principal filter combinations
3. Uses the `get_distinct_resource_query_filters()` method to extract unique resource filter combinations
4. Builds a matrix where each cell aggregates actions from all rules matching that (resource, resource filter, principal filter) combination

## Key Features

- **Dynamic Structure**: The report automatically adjusts its columns and rows based on the configured rules
- **Exception Handling**: Exception filters are clearly marked with ⚠️ emoji
- **Aggregation**: When multiple rules apply to the same combination, their actions are aggregated
- **Date Range Filtering**: Only shows rules within their valid date range
- **Action Filtering**: Optional Y/N display for specific action auditing

## Comparison with AC Resource Rules

| Feature | AC Rules | AC Resource Rules |
|---------|----------|-------------------|
| Scope | All resources, all rules | Single resource |
| Rows | (Resource, Resource Filter) | Users |
| Columns | Principal Filters | Resource Filters |
| Cells | Aggregated Actions | Aggregated Actions |
| Best For | System-wide overview | Resource-specific user access |

## Example

Consider these rules:

**Rule 1**: Permit "Sales Team" to Read/Write "Active Customers"
**Rule 2**: Permit "Sales Managers" to Read/Write/Delete "Active Customers"
**Rule 3**: Permit "Sales Team" to Read "All Customers"

The report would show:

| Resource | Resource Filter | Sales Team | Sales Managers |
|----------|----------------|------------|----------------|
| Customer | Active Customers | Read, Write | Read, Write, Delete |
| Customer | All | Read | |

With Action Filter = "Read":

| Resource | Resource Filter | Sales Team | Sales Managers |
|----------|----------------|------------|----------------|
| Customer | Active Customers | Y | Y |
| Customer | All | Y | N |

## Permissions

This report is restricted to System Manager role.
