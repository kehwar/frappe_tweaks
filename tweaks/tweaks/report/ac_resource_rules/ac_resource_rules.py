# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub

from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import (
    check_user_matches_rule_principals,
    get_principal_filter_sql,
)


def execute(filters=None):
    """
    AC Resource Rules Report
    
    Matrix view showing which users have access based on principal query filters.
    
    Filters:
        - resource (required): AC Resource to analyze
        - query_filter (optional): Query Filter for user filtering (User, User Group, Role, or Role Profile)
    
    Report Structure:
        - Rows: Users (all enabled, or filtered by Query Filter)
        - Columns: Principal Query Filters from AC Rules (grouped and de-duplicated)
        - Cells: Comma-separated actions if user matches the filter
    
    Column Logic:
        - Each non-exception principal filter becomes a column
        - Exception filters multiply columns (e.g., "Allow1 - ⚠️ Forbid1, ⚠️ Forbid2")
        - If multiple rules use the same filter, actions aggregate in that column
        - Column labels show filter names with emoji (✅ Permit, 🚫 Forbid based on rule type; ⚠️ for exception filters)
    
    The report evaluates each user against principal filters and displays allowed actions.
    Only enabled rules within valid date ranges are shown.
    """
    columns = []
    data = []

    if not filters or not filters.get("resource"):
        return columns, data

    columns, data = get_data(filters)
    return columns, data


def get_data(filters):
    """Get permission data for the selected resource"""

    resource_name = filters.get("resource")
    query_filter_name = filters.get("query_filter")

    # Get the AC Resource
    resource = frappe.get_doc("AC Resource", resource_name)

    # Get all AC Rules for this resource
    ac_rules = frappe.get_all(
        "AC Rule",
        filters={
            "resource": resource_name,
            "disabled": 0,
        },
        fields=["name", "title", "type", "valid_from", "valid_upto"],
        order_by="name",
    )

    # Filter rules by valid date range
    ac_rules = [
        r
        for r in ac_rules
        if (not r.valid_from or r.valid_from <= frappe.utils.getdate())
        and (not r.valid_upto or r.valid_upto >= frappe.utils.getdate())
    ]

    if not ac_rules:
        return [], []

    # Get all users (or filtered users if query filter is provided)
    users = get_users(query_filter_name)

    if not users:
        return [], []

    # Build filter columns by analyzing all rules
    filter_columns = build_filter_columns(ac_rules)

    if not filter_columns:
        return [], []

    # Build columns: User + one column per filter combination
    columns = [
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 250,
        },
    ]

    for col in filter_columns:
        columns.append(
            {
                "fieldname": col["fieldname"],
                "label": col["label"],
                "fieldtype": "Data",
                "width": 200,
            }
        )

    # Build data rows
    data = []
    for user in users:
        row = {"user": user}

        # For each filter column, check if the user matches and aggregate actions
        for col in filter_columns:
            actions = get_user_actions_for_filter_column(user, col, ac_rules)
            row[col["fieldname"]] = actions

        data.append(row)

    return columns, data


def build_filter_columns(ac_rules):
    """
    Build columns based on principal query filters from all rules.
    
    Returns a list of column definitions with:
    - fieldname: unique identifier for the column
    - label: display name with emojis
    - principals: list of principal objects (with name, doctype, exception fields) for matching
    - rules: list of rule info (name, type, actions) that use this filter combination
    """
    # Dictionary to group filters: key = (tuple of allowed filters, tuple of denied filters)
    filter_groups = {}

    for rule_info in ac_rules:
        rule = frappe.get_doc("AC Rule", rule_info.name)
        principals = rule.resolve_principals()

        # Separate allowed and denied principals
        allowed = [p for p in principals if not p.get("exception", 0)]
        denied = [p for p in principals if p.get("exception", 0)]

        # Get actions for this rule
        actions = [action.action for action in rule.actions]

        # If there are no denied filters, create one entry per allowed filter
        if not denied:
            for allow_filter in allowed:
                key = (tuple([allow_filter["name"]]), tuple())
                if key not in filter_groups:
                    filter_groups[key] = {
                        "principals": [allow_filter],
                        "rules": []
                    }
                filter_groups[key]["rules"].append({
                    "name": rule.name,
                    "type": rule.type,
                    "actions": actions
                })
        else:
            # With denied filters, create one column per allowed filter with ALL denied filters
            # For example: allow1, allow2, forbid1, forbid2 creates:
            # - allow1, forbid1, forbid2
            # - allow2, forbid1, forbid2
            denied_names = tuple(sorted([d["name"] for d in denied]))
            for allow_filter in allowed:
                key = (tuple([allow_filter["name"]]), denied_names)
                if key not in filter_groups:
                    # Combine allowed and denied principals for this combination
                    combined_principals = [allow_filter] + denied
                    filter_groups[key] = {
                        "principals": combined_principals,
                        "rules": []
                    }
                filter_groups[key]["rules"].append({
                    "name": rule.name,
                    "type": rule.type,
                    "actions": actions
                })

    # Build column definitions
    columns = []
    for idx, (key, group) in enumerate(sorted(filter_groups.items())):
        # Extract filter names for display
        allowed_names = [p["name"] for p in group["principals"] if not p.get("exception", 0)]
        denied_names = [p["name"] for p in group["principals"] if p.get("exception", 0)]

        # Build label with filter names
        if denied_names:
            # Add emoji before each exception filter
            denied_with_emoji = [f"⚠️ {name}" for name in denied_names]
            label = f"{', '.join(allowed_names)} - {', '.join(denied_with_emoji)}"
        else:
            label = ", ".join(allowed_names)

        # Add emoji based on rule types (use first rule's type as indicator)
        if group["rules"]:
            first_rule_type = group["rules"][0]["type"]
            emoji = "✅" if first_rule_type == "Permit" else "🚫"
            label = f"{emoji} {label}"

        columns.append({
            "fieldname": f"filter_{idx}",
            "label": label,
            "principals": group["principals"],
            "rules": group["rules"]
        })

    return columns


def get_user_actions_for_filter_column(user, column, ac_rules):
    """
    Check if a user matches the filter column's criteria and return aggregated actions.
    Uses the check_user_matches_rule_principals utility function.
    """
    all_actions = set()

    # Check if user matches the principals for this column
    if check_user_matches_rule_principals(user, column["principals"]):
        # User matches - add all actions from rules in this column
        for rule_info in column["rules"]:
            all_actions.update(rule_info["actions"])

    return ", ".join(sorted(all_actions)) if all_actions else ""


def get_users(query_filter_name=None):
    """Get list of users, optionally filtered by a Query Filter"""

    if query_filter_name:
        # Get users matching the query filter
        query_filter = frappe.get_doc("Query Filter", query_filter_name)

        # Validate that the filter is for User-related doctypes
        if query_filter.reference_doctype not in [
            "User",
            "User Group",
            "Role",
            "Role Profile",
        ]:
            frappe.throw(
                _(
                    "Query Filter must reference User, User Group, Role, or Role Profile"
                )
            )

        # Get the SQL from the filter
        filter_sql = get_principal_filter_sql(query_filter)

        if not filter_sql:
            return []

        # Execute the query to get users
        users = frappe.db.sql(
            f"SELECT DISTINCT `name` FROM `tabUser` WHERE {filter_sql} AND enabled = 1 ORDER BY `name`",
            pluck="name",
        )

        return users
    else:
        # Get all enabled users
        return frappe.db.get_all("User", filters={"enabled": 1}, pluck="name", order_by="name")

