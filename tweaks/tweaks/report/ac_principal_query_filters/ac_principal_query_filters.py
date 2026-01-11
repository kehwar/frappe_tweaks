# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_principal_filter_sql


def execute(filters=None):
    """
    AC Principal Query Filters Report

    Shows each principal query filter (User, Role, User Group, Role Profile)
    with the SQL used to determine users and lists all matching users.

    Report Structure:
        - Rows: One row per (Query Filter, User) combination
        - Columns: Query Filter, Reference DocType, Reference DocName, Filter Type, Filter, SQL, User

    The report helps understand which users are matched by each principal filter.
    Includes Query Filter properties and a button to view filter code in a dialog.
    """
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "fieldname": "filter_name",
            "label": _("Filter Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "query_filter",
            "label": _("Query Filter"),
            "fieldtype": "Link",
            "options": "Query Filter",
            "hidden": 1,
        },
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "user_id",
            "label": _("User ID"),
            "fieldtype": "Link",
            "options": "User",
            "hidden": 1,
        },
        {
            "fieldname": "reference_doctype",
            "label": _("Reference DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 150,
        },
        {
            "fieldname": "reference_docname",
            "label": _("Reference DocName"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "filters_type",
            "label": _("Filter Type"),
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "fieldname": "filters",
            "label": _("Filter"),
            "fieldtype": "Code",
            "width": 120,
        },
        {
            "fieldname": "sql",
            "label": _("SQL"),
            "fieldtype": "Data",
            "width": 300,
        },
    ]


def get_data(filters):
    """Get data for the report"""

    # Get all Query Filters of relevant types
    query_filters = frappe.get_all(
        "Query Filter",
        filters={
            "reference_doctype": ["in", ["User", "Role", "User Group", "Role Profile"]],
            "disabled": 0,
        },
        fields=[
            "name",
            "filter_name",
            "reference_doctype",
            "reference_docname",
            "filters_type",
            "filters",
        ],
        order_by="name",
    )

    data = []

    for qf_info in query_filters:
        # Load the full Query Filter document
        query_filter = frappe.get_doc("Query Filter", qf_info.name)

        # Get the SQL for this filter
        try:
            filter_sql = get_principal_filter_sql(query_filter)

            # Remove line breaks from SQL
            filter_sql_display = (
                filter_sql.replace("\n", " ").replace("\r", " ").strip()
            )

            # Get users matching this filter
            if filter_sql:
                users = frappe.db.sql(
                    f"""
                    SELECT DISTINCT `name`, `full_name`
                    FROM `tabUser`
                    WHERE {filter_sql} AND enabled = 1
                    ORDER BY `name`
                    """,
                    as_dict=1,
                )
            else:
                users = []

            # Create a row for each user
            for user in users:
                data.append(
                    {
                        "filter_name": qf_info.filter_name,
                        "query_filter": qf_info.name,
                        "reference_doctype": qf_info.reference_doctype,
                        "reference_docname": qf_info.reference_docname,
                        "filters_type": qf_info.filters_type,
                        "filters": qf_info.filters,
                        "sql": filter_sql_display,
                        "user": user["full_name"],
                        "user_id": user["name"],
                    }
                )

        except Exception as e:
            # If there's an error getting SQL or users, log it and skip this filter
            frappe.log_error(
                f"Error processing Query Filter {qf_info.name}: {str(e)}",
                "AC Principal Query Filters Report",
            )
            continue

    return data
