# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub


def execute(filters=None):
    """
    AC Rules Report
    
    Matrix view showing access control rules with:
    - Rows: Unique combinations of (resource, resource query filter)
    - Columns: Distinct principal query filters
    - Cells: Aggregated actions for each (row, column) combination
    
    Filters:
        - action (optional): Specific action to check (shows Y/N instead of listing all actions)
    
    Report Structure:
        The report provides a bird's-eye view of all access control rules in the system.
        Each row represents a unique combination of a resource and one of its resource query filters.
        Each column represents a distinct principal query filter used across all rules.
        Cells show which actions are granted (or Y/N if action filter is specified).
    
    Only enabled rules within valid date ranges are shown.
    """
    columns = []
    data = []

    columns, data = get_data(filters)
    return columns, data


def get_data(filters):
    """Get access control rule data"""

    # Get all enabled AC Rules within valid date range
    ac_rules = frappe.get_all(
        "AC Rule",
        filters={
            "disabled": 0,
        },
        fields=["name", "title", "type", "resource", "valid_from", "valid_upto"],
        order_by="name",
    )

    # Filter rules by valid date range
    today = frappe.utils.getdate()
    ac_rules = [
        r
        for r in ac_rules
        if (not r.valid_from or r.valid_from <= today)
        and (not r.valid_upto or r.valid_upto >= today)
    ]

    if not ac_rules:
        return [], []

    # Build rows: unique combinations of (resource, resource query filter)
    rows = build_rows(ac_rules)

    if not rows:
        return [], []

    # Build columns: distinct principal query filters
    columns_list = build_columns(ac_rules)

    if not columns_list:
        return [], []

    # Build report columns structure
    columns = [
        {
            "fieldname": "resource",
            "label": _("Resource"),
            "fieldtype": "Link",
            "options": "AC Resource",
            "width": 200,
        },
        {
            "fieldname": "resource_filter",
            "label": _("Resource Filter"),
            "fieldtype": "Data",
            "width": 200,
        },
    ]

    for col in columns_list:
        columns.append(
            {
                "fieldname": col["fieldname"],
                "label": col["label"],
                "fieldtype": "Data",
                "width": 150,
            }
        )

    # Build data rows
    data = []
    action_filter = filters.get("action") if filters else None

    for row in rows:
        # Display "All" for None resource filter
        resource_filter_display = row["resource_filter"] if row["resource_filter"] else "All"
        
        data_row = {
            "resource": row["resource"],
            "resource_filter": resource_filter_display,
        }

        # For each column (principal filter), find matching actions
        for col in columns_list:
            actions = get_actions_for_cell(
                row["resource"],
                row["resource_filter"],
                row["resource_exception"],
                col["principal_filter"],
                col["principal_exception"],
                ac_rules,
            )

            # If action filter is specified, show Y/N instead of listing actions
            if action_filter:
                data_row[col["fieldname"]] = "Y" if action_filter in actions else "N"
            else:
                data_row[col["fieldname"]] = ", ".join(sorted(actions)) if actions else ""

        data.append(data_row)

    return columns, data


def build_rows(ac_rules):
    """
    Build rows based on unique combinations of (resource, resource query filter).
    
    For each rule, extract all distinct resource query filter combinations
    using the get_distinct_resource_query_filters method.
    
    If a rule has no resource filters (applies to all), it creates a row with
    resource_filter = None (shown as "All" in the report).
    
    Returns a list of row definitions with:
    - resource: AC Resource name
    - resource_filter: Query Filter name (non-exception), or None for "All"
    - resource_exception: Tuple of exception filter names
    """
    rows_dict = {}

    for rule_info in ac_rules:
        rule = frappe.get_doc("AC Rule", rule_info.name)

        # Get distinct resource query filter combinations
        distinct_combos = rule.get_distinct_resource_query_filters()

        # If no resource filters, create a row for "All"
        if not distinct_combos:
            key = (rule.resource, None, tuple())
            if key not in rows_dict:
                rows_dict[key] = {
                    "resource": rule.resource,
                    "resource_filter": None,  # None means "All"
                    "resource_exception": tuple(),
                }
        else:
            for rule_type, resource_filter, exception_tuple in distinct_combos:
                # Create a unique key for this row
                key = (rule.resource, resource_filter, exception_tuple)

                if key not in rows_dict:
                    rows_dict[key] = {
                        "resource": rule.resource,
                        "resource_filter": resource_filter,
                        "resource_exception": exception_tuple,
                    }

    # Convert to sorted list (None sorts first)
    rows = sorted(
        rows_dict.values(),
        key=lambda x: (x["resource"], x["resource_filter"] or "", x["resource_exception"]),
    )

    return rows


def build_columns(ac_rules):
    """
    Build columns based on distinct principal query filters.
    
    For each rule, extract all distinct principal query filter combinations
    using the get_distinct_principal_query_filters method.
    
    Returns a list of column definitions with:
    - fieldname: unique identifier for the column
    - label: display name with filter name and exceptions
    - principal_filter: Query Filter name (non-exception)
    - principal_exception: Tuple of exception filter names
    """
    columns_dict = {}

    for rule_info in ac_rules:
        rule = frappe.get_doc("AC Rule", rule_info.name)

        # Get distinct principal query filter combinations
        distinct_combos = rule.get_distinct_principal_query_filters()

        for rule_type, principal_filter, exception_tuple in distinct_combos:
            # Create a unique key for this column
            key = (principal_filter, exception_tuple)

            if key not in columns_dict:
                # Build label
                if exception_tuple:
                    exception_labels = [f"⚠️ {name}" for name in exception_tuple]
                    label = f"{principal_filter} - {', '.join(exception_labels)}"
                else:
                    label = principal_filter

                columns_dict[key] = {
                    "fieldname": f"col_{len(columns_dict)}",
                    "label": label,
                    "principal_filter": principal_filter,
                    "principal_exception": exception_tuple,
                }

    # Convert to sorted list
    columns_list = sorted(
        columns_dict.values(), key=lambda x: (x["principal_filter"], x["principal_exception"])
    )

    return columns_list


def get_actions_for_cell(
    resource,
    resource_filter,
    resource_exception,
    principal_filter,
    principal_exception,
    ac_rules,
):
    """
    Get aggregated actions for a specific cell (row, column combination).
    
    Find all rules that match:
    - The resource
    - Have the principal filter (and same exceptions)
    - Have the resource filter (and same exceptions), or None for "All"
    
    Returns a set of action names.
    """
    actions = set()

    for rule_info in ac_rules:
        rule = frappe.get_doc("AC Rule", rule_info.name)

        # Check if rule matches the resource
        if rule.resource != resource:
            continue

        # Check if rule has matching principal filter combination
        principal_combos = rule.get_distinct_principal_query_filters()
        principal_match = any(
            pf == principal_filter and pe == principal_exception
            for rt, pf, pe in principal_combos
        )

        if not principal_match:
            continue

        # Check if rule has matching resource filter combination
        resource_combos = rule.get_distinct_resource_query_filters()
        
        # If resource_filter is None, we're looking for rules with no resource filters
        if resource_filter is None:
            # Match if rule has no resource filters
            resource_match = len(resource_combos) == 0
        else:
            # Match if rule has this specific resource filter combination
            resource_match = any(
                rf == resource_filter and re == resource_exception
                for rt, rf, re in resource_combos
            )

        if not resource_match:
            continue

        # Rule matches - add its actions
        for action in rule.actions:
            actions.add(action.action)

    return actions
