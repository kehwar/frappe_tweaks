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


def get_flat_data(filters):
    """
    Get flat report data.

    Each row represents a unique combination of:
    - Resource
    - Principal Filter (with exceptions and rule type)
    - Resource Filter (with exceptions and rule type)

    Returns columns and data for flat report view.
    """
    # Get all enabled AC Rules within valid date range
    ac_rules_dict = get_enabled_ac_rules()

    if not ac_rules_dict:
        return [], []

    # Get filter display names cache
    filter_display_names = get_filter_display_names_cache(ac_rules_dict)

    # Build flat data: one row per (resource, principal filter, resource filter) combination
    flat_rows = []

    for rule_name, rule in ac_rules_dict.items():
        resource_name = rule.resource
        resource_title = get_resource_title(resource_name)

        # Get distinct principal and resource filter combinations
        principal_combos = rule.get_distinct_principal_query_filters()
        resource_combos = rule.get_distinct_resource_query_filters()

        # If no resource filters, treat as "All"
        if not resource_combos:
            resource_combos = [(rule.type, None, ())]

        # Create a row for each combination
        for p_rule_type, p_filter, p_exceptions in principal_combos:
            for r_rule_type, r_filter, r_exceptions in resource_combos:
                # Create unique key for this combination
                key = (
                    resource_name,
                    p_filter,
                    p_exceptions,
                    p_rule_type,
                    r_filter,
                    r_exceptions,
                    r_rule_type,
                )

                # Find or create row
                existing_row = None
                for row in flat_rows:
                    if row["_key"] == key:
                        existing_row = row
                        break

                if existing_row:
                    # Add actions to existing row
                    for action in rule.actions:
                        existing_row["_actions"].add(action.action)
                else:
                    # Create new row
                    actions_set = set()
                    for action in rule.actions:
                        actions_set.add(action.action)

                    flat_rows.append(
                        {
                            "_key": key,
                            "resource_name": resource_name,
                            "resource_title": resource_title,
                            "principal_filter": p_filter,
                            "principal_exception": p_exceptions,
                            "principal_rule_type": p_rule_type,
                            "resource_filter": r_filter,
                            "resource_exception": r_exceptions,
                            "resource_rule_type": r_rule_type,
                            "_actions": actions_set,
                        }
                    )

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
            "fieldname": "resource",
            "label": _("Resource"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "principal_filter",
            "label": _("Principal Filter"),
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "resource_filter",
            "label": _("Resource Filter"),
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "actions",
            "label": _("Actions"),
            "fieldtype": "Data",
            "width": 200,
        },
    ]

    # Build data rows
    data = []
    action_filter = filters.get("action")

    for row in flat_rows:
        # Format principal filter display
        principal_display = format_filter_display(
            row["principal_filter"],
            row["principal_exception"],
            row["principal_rule_type"],
            filter_display_names,
        )

        # Format resource filter display
        resource_display = format_filter_display(
            row["resource_filter"],
            row["resource_exception"],
            row["resource_rule_type"],
            filter_display_names,
        )

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
                "resource": row["resource_title"],
                "principal_filter": principal_display,
                "resource_filter": resource_display,
                "actions": actions_display,
            }
        )

    # Sort data
    data.sort(
        key=lambda x: (x["resource"], x["principal_filter"], x["resource_filter"])
    )

    return columns, data
