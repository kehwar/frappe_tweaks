# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    """Generate report of all Event Scripts"""
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "fieldname": "name",
            "label": _("Name"),
            "fieldtype": "Link",
            "options": "Event Script",
            "width": 120,
        },
        {
            "fieldname": "title",
            "label": _("Title"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "document_type",
            "label": _("Document Type"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 150,
        },
        {
            "fieldname": "document_type_group",
            "label": _("Document Type Group"),
            "fieldtype": "Link",
            "options": "DocType Group",
            "width": 150,
        },
        {
            "fieldname": "doctype_event",
            "label": _("Event"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "action",
            "label": _("Action"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "workflow_action",
            "label": _("Workflow Action"),
            "fieldtype": "Link",
            "options": "Workflow Action Master",
            "width": 150,
        },
        {
            "fieldname": "priority",
            "label": _("Priority"),
            "fieldtype": "Int",
            "width": 80,
        },
        {
            "fieldname": "disabled",
            "label": _("Disabled"),
            "fieldtype": "Check",
            "width": 80,
        },
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 120,
        },
        {
            "fieldname": "user_group",
            "label": _("User Group"),
            "fieldtype": "Link",
            "options": "User Group",
            "width": 120,
        },
        {
            "fieldname": "role",
            "label": _("Role"),
            "fieldtype": "Link",
            "options": "Role",
            "width": 120,
        },
        {
            "fieldname": "role_profile",
            "label": _("Role Profile"),
            "fieldtype": "Link",
            "options": "Role Profile",
            "width": 120,
        },
        {
            "fieldname": "script",
            "label": _("Script"),
            "fieldtype": "Code",
            "width": 120,
        },
        {
            "fieldname": "parameters",
            "label": _("Parameters"),
            "fieldtype": "Code",
            "width": 120,
        },
    ]


def get_data(filters):
    """Fetch Event Script data"""
    conditions = []
    values = {}

    # Build filter conditions
    if filters.get("document_type"):
        conditions.append("document_type = %(document_type)s")
        values["document_type"] = filters.get("document_type")

    if filters.get("document_type_group"):
        conditions.append("document_type_group = %(document_type_group)s")
        values["document_type_group"] = filters.get("document_type_group")

    if filters.get("doctype_event"):
        conditions.append("doctype_event = %(doctype_event)s")
        values["doctype_event"] = filters.get("doctype_event")

    if filters.get("action"):
        conditions.append("action = %(action)s")
        values["action"] = filters.get("action")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            name,
            title,
            document_type,
            document_type_group,
            doctype_event,
            action,
            workflow_action,
            priority,
            disabled,
            user,
            user_group,
            role,
            role_profile,
            script
        FROM
            `tabEvent Script`
        {where_clause}
        ORDER BY
            disabled ASC,
            priority DESC,
            document_type ASC,
            doctype_event ASC,
            title ASC
    """

    data = frappe.db.sql(query, values, as_dict=1)

    # Fetch parameters for each event script
    for row in data:
        parameters = frappe.get_all(
            "Event Script Parameter",
            filters={"parent": row.name},
            fields=["document_type", "document_name", "field", "value"],
            order_by="idx",
        )
        row["parameters"] = parameters if parameters else None

    return data
