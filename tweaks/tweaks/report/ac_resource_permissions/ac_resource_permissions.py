# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub

from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_principal_filter_sql


def execute(filters=None):
    """Generate AC Resource Permissions report"""
    columns = []
    data = []

    if not filters or not filters.get("resource"):
        frappe.msgprint(_("Please select a Resource"))
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
        frappe.msgprint(_("No AC Rules found for the selected Resource"))
        return [], []

    # Get all users (or filtered users if query filter is provided)
    users = get_users(query_filter_name)

    if not users:
        frappe.msgprint(_("No users found"))
        return [], []

    # Build columns: User + one column per AC Rule
    columns = [
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 250,
        },
    ]

    # Add a column for each AC Rule with emoji in the name
    for rule in ac_rules:
        emoji = "✅" if rule.type == "Permit" else "🚫"
        columns.append(
            {
                "fieldname": f"rule_{scrub(rule.name)}",
                "label": f"{emoji} {rule.title}",
                "fieldtype": "Data",
                "width": 200,
            }
        )

    # Build data rows
    data = []
    for user in users:
        row = {"user": user}

        # For each AC Rule, check if the user matches the principals
        # and if so, show the actions
        for rule in ac_rules:
            actions = get_user_actions_for_rule(user, rule.name, resource)
            row[f"rule_{scrub(rule.name)}"] = actions

        data.append(row)

    return columns, data


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


def get_user_actions_for_rule(user, rule_name, resource):
    """
    Check if a user matches the principals of a rule,
    and if so, return the actions as a concatenated string
    """

    # Get the AC Rule document
    rule = frappe.get_doc("AC Rule", rule_name)

    # Resolve principals to check if user matches
    principals = rule.resolve_principals()

    # Build the SQL to check if user matches any principal filters
    allowed = [
        get_principal_filter_sql(p) for p in principals if p.get("exception", 0) == 0
    ]
    denied = [
        get_principal_filter_sql(p) for p in principals if p.get("exception", 0) == 1
    ]

    # Remove empty SQL statements
    allowed = [sql for sql in allowed if sql]
    denied = [sql for sql in denied if sql]

    if not allowed:
        return ""

    # Build the final query
    allowed_sql = " OR ".join([f"({q})" for q in allowed]) if len(allowed) > 1 else allowed[0]
    denied_sql = " OR ".join([f"({q})" for q in denied]) if len(denied) > 1 else (denied[0] if denied else "")

    # Check if user matches
    if denied_sql:
        user_check_sql = f"SELECT 1 FROM `tabUser` WHERE `name` = {frappe.db.escape(user)} AND ({allowed_sql}) AND NOT ({denied_sql})"
    else:
        user_check_sql = f"SELECT 1 FROM `tabUser` WHERE `name` = {frappe.db.escape(user)} AND ({allowed_sql})"

    user_matches = frappe.db.sql(user_check_sql)

    if not user_matches:
        return ""

    # User matches - return the actions
    actions = [action.action for action in rule.actions]

    return ", ".join(actions)
