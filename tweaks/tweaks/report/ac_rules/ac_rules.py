# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub


def execute(filters=None):
    """
    AC Rules Report

    The AC Rules report provides a comprehensive view of all access control rules in the system.

    Columns:
        - Resource: The AC Resource (DocType or Report)
        - Principal Filter: Query Filter defining which users/roles the rule applies to
        - Resource Filter: Query Filter defining which records the rule applies to (or "All")
        - Actions: List of actions granted/denied by matching rules

    Each row shows one unique combination of (resource, principal filter, resource filter)
    with aggregated actions from all matching rules.

    Filters:
        - action (optional): Filter by specific action. Shows Y/N for that specific action.
        - principal_filter (optional): Filter by Query Filter (User, User Group, or Role). Only shows users matching the selected filter.

    Use Cases:
        1. Comprehensive Access Audit: View all access control rules
        2. Action-Specific Auditing: Filter by action to see which combinations grant that action
        3. Gap Analysis: Identify resources without access rules
        4. Over-Permission Detection: Identify principals with excessive access

    Only enabled rules within valid date ranges are shown.
    """
    filters = filters or {}
    return get_flat_data(filters)


def get_enabled_ac_rules():
    """Get all enabled AC Rules within valid date range"""
    ac_rules_meta = frappe.get_all(
        "AC Rule",
        filters={"disabled": 0},
        fields=["name", "title", "type", "resource", "valid_from", "valid_upto"],
        order_by="name",
    )

    # Filter rules by valid date range
    today = frappe.utils.getdate()
    ac_rules_meta = [
        r
        for r in ac_rules_meta
        if (not r.valid_from or r.valid_from <= today)
        and (not r.valid_upto or r.valid_upto >= today)
    ]

    # Load all AC Rule documents once to avoid N³ database queries
    ac_rules_dict = {}
    for rule_meta in ac_rules_meta:
        ac_rules_dict[rule_meta.name] = frappe.get_doc("AC Rule", rule_meta.name)

    return ac_rules_dict


def get_filter_display_names_cache(ac_rules_dict):
    """Get display names for all query filters used in the rules"""
    all_filter_names = set()

    for rule_name, rule in ac_rules_dict.items():
        # Collect principal filter names
        for row in rule.principals:
            all_filter_names.add(row.filter)

        # Collect resource filter names
        for row in rule.resources:
            all_filter_names.add(row.filter)

    # Fetch display names
    filter_display_names = {}
    if all_filter_names:
        filter_docs = frappe.get_all(
            "Query Filter",
            filters={"name": ["in", list(all_filter_names)]},
            fields=["name", "filter_name"],
        )
        filter_display_names = {doc.name: doc.filter_name for doc in filter_docs}

    return filter_display_names


def get_resource_title(resource_name):
    """Get display title for a resource"""
    resource_doc = frappe.get_cached_doc("AC Resource", resource_name)
    return resource_doc.title or resource_name


def format_filter_display(
    filter_name, exception_tuple, rule_type, filter_display_names
):
    """
    Format filter display with exceptions and rule type emoji.

    Args:
        filter_name: Query filter name (or None for "All")
        exception_tuple: Tuple of exception filter names
        rule_type: "Permit" or "Forbid"
        filter_display_names: Dict mapping filter names to display names

    Returns:
        Formatted display string
    """
    if filter_name is None:
        display = "All"
    else:
        display = filter_display_names.get(filter_name, filter_name)

        # Add exceptions if present
        if exception_tuple:
            exception_names = [
                filter_display_names.get(e, e) for e in sorted(exception_tuple)
            ]
            display += f" ⚠️ ({', '.join(exception_names)})"

    # Add emoji for Forbid type
    if rule_type == "Forbid":
        display = f"🚫 {display}"

    return display


def resolve_principals_to_users(rule):
    """
    Resolve all principal filters in a rule to get list of users.

    Args:
        rule: AC Rule document

    Returns:
        List of user dictionaries with 'name' and 'full_name'
    """
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_principal_filter_sql

    # Build SQL to get users matching all principal filters (including exceptions)
    allowed_filters = []
    denied_filters = []

    for row in rule.principals:
        if row.exception:
            denied_filters.append(row.filter)
        else:
            allowed_filters.append(row.filter)

    if not allowed_filters:
        return []

    # Build SQL for allowed users
    allowed_sql_parts = []
    for filter_name in allowed_filters:
        try:
            query_filter = frappe.get_cached_doc("Query Filter", filter_name)
            filter_sql = get_principal_filter_sql(query_filter)
            if filter_sql:
                allowed_sql_parts.append(f"({filter_sql})")
        except Exception as e:
            frappe.log_error(f"Error getting SQL for filter {filter_name}: {str(e)}")

    if not allowed_sql_parts:
        return []

    # Combine with OR
    allowed_sql = " OR ".join(allowed_sql_parts)

    # Build SQL for denied users
    denied_sql_parts = []
    for filter_name in denied_filters:
        try:
            query_filter = frappe.get_cached_doc("Query Filter", filter_name)
            filter_sql = get_principal_filter_sql(query_filter)
            if filter_sql:
                denied_sql_parts.append(f"({filter_sql})")
        except Exception as e:
            frappe.log_error(
                f"Error getting SQL for denied filter {filter_name}: {str(e)}"
            )

    # Combine final SQL
    final_sql = f"({allowed_sql})"
    if denied_sql_parts:
        denied_sql = " OR ".join(denied_sql_parts)
        final_sql = f"({final_sql}) AND NOT ({denied_sql})"

    # Get users
    users = frappe.db.sql(
        f"""
        SELECT DISTINCT `name`, `full_name`
        FROM `tabUser`
        WHERE {final_sql} AND enabled = 1
        ORDER BY `name`
        """,
        as_dict=1,
    )

    return users


def get_flat_data(filters):
    """
    Get flat report data.

    Steps:
    1. List all rules
    2. Resolve principals for each rule to get list of all users
    3. Resolve resources for each rule to get distinct resource filters
    4. For each (user, distinct resource filter) combination, create a row and aggregate actions

    Returns columns and data for flat report view.
    """
    # Step 1: Get all enabled AC Rules within valid date range
    ac_rules_dict = get_enabled_ac_rules()

    if not ac_rules_dict:
        return [], []

    # Get filter display names cache
    filter_display_names = get_filter_display_names_cache(ac_rules_dict)

    # Build flat data: one row per (user, resource, resource filter) combination
    flat_rows = {}

    # Get principal filter if specified
    principal_filter_name = filters.get("principal_filter")
    principal_filter_users = None
    if principal_filter_name:
        # Get users matching the principal filter
        try:
            from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import (
                get_principal_filter_sql,
            )

            query_filter = frappe.get_cached_doc("Query Filter", principal_filter_name)
            filter_sql = get_principal_filter_sql(query_filter)
            if filter_sql:
                users_result = frappe.db.sql(
                    f"""
                    SELECT DISTINCT `name`
                    FROM `tabUser`
                    WHERE {filter_sql} AND enabled = 1
                    """,
                    as_dict=1,
                )
                principal_filter_users = {u["name"] for u in users_result}
            else:
                principal_filter_users = set()
        except Exception as e:
            frappe.log_error(
                f"Error resolving principal filter {principal_filter_name}: {str(e)}"
            )
            principal_filter_users = set()

    # Step 2-4: For each rule, resolve principals and resources, then create rows
    for rule_name, rule in ac_rules_dict.items():
        resource_name = rule.resource
        resource_title = get_resource_title(resource_name)

        # Step 2: Resolve principals to get users
        try:
            users = resolve_principals_to_users(rule)
        except Exception as e:
            frappe.log_error(
                f"Error resolving principals for rule {rule_name}: {str(e)}"
            )
            users = []

        # Step 3: Resolve resources to get distinct resource query filters
        resource_combos = rule.get_distinct_resource_query_filters()

        # If no resource filters, treat as "All"
        if not resource_combos:
            resource_combos = [(rule.type, None, ())]

        # Step 4: For each (user, distinct resource filter) combination, create/update row
        for user in users:
            # Filter by principal_filter if specified
            if (
                principal_filter_users is not None
                and user["name"] not in principal_filter_users
            ):
                continue

            for r_rule_type, r_filter, r_exceptions in resource_combos:
                # Create unique key for this combination
                key = (
                    user["name"],
                    resource_name,
                    r_filter,
                    r_exceptions,
                    r_rule_type,
                )

                # Find or create row
                if key in flat_rows:
                    # Add actions to existing row
                    for action in rule.actions:
                        flat_rows[key]["_actions"].add(action.action)
                else:
                    # Create new row
                    actions_set = set()
                    for action in rule.actions:
                        actions_set.add(action.action)

                    flat_rows[key] = {
                        "_key": key,
                        "user_name": user["name"],
                        "user_full_name": user["full_name"],
                        "resource_name": resource_name,
                        "resource_title": resource_title,
                        "resource_filter": r_filter,
                        "resource_exception": r_exceptions,
                        "resource_rule_type": r_rule_type,
                        "_actions": actions_set,
                    }

    # Build columns
    columns = [
        {
            "fieldname": "resource_name",
            "label": _("Resource Name"),
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1,
        },
        {
            "fieldname": "user_id",
            "label": _("User ID"),
            "fieldtype": "Link",
            "options": "User",
            "width": 0,
            "hidden": 1,
        },
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "resource",
            "label": _("Resource"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "rule_type",
            "label": _("Rule Type"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "distinct_resource_query_filters",
            "label": _("Distinct Resource Query Filters"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "actions",
            "label": _("Actions"),
            "fieldtype": "Data",
            "width": 200,
        },
    ]

    # Build data rows from dictionary
    data = []
    action_filter = filters.get("action")

    for row in flat_rows.values():
        # Format resource filter display - without rule type emoji
        resource_filter_display = format_filter_display(
            row["resource_filter"],
            row["resource_exception"],
            "Permit",  # Don't show rule type emoji in resource filter column
            filter_display_names,
        )

        # Rule type
        rule_type = row["resource_rule_type"]

        # Format actions
        if action_filter:
            actions_display = "Y" if action_filter in row["_actions"] else "N"
        else:
            actions_display = (
                ", ".join(sorted(row["_actions"])) if row["_actions"] else ""
            )

        data.append(
            {
                "resource_name": row["resource_name"],
                "user": row["user_full_name"] or row["user_name"],
                "user_id": row["user_name"],
                "resource": row["resource_title"],
                "rule_type": rule_type,
                "distinct_resource_query_filters": resource_filter_display,
                "actions": actions_display,
            }
        )

    # Sort data
    data.sort(
        key=lambda x: (x["user"], x["resource"], x["distinct_resource_query_filters"])
    )

    return columns, data
