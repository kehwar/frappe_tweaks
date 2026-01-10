# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    """
    Query Filters Report
    
    Lists all Query Filters with their calculated SQL.
    
    Filters:
        - impersonate_user (optional): User to impersonate when calculating SQL
    
    This report shows:
        - Filter Name
        - Reference DocType/Report
        - Filter Type
        - Disabled status
        - Calculated SQL (as the impersonated user or current user)
    """
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
            "options": "Query Filter",
            "width": 120,
        },
        {
            "fieldname": "filter_name",
            "label": _("Filter Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "reference_doctype",
            "label": _("Reference DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 150,
        },
        {
            "fieldname": "reference_report",
            "label": _("Reference Report"),
            "fieldtype": "Link",
            "options": "Report",
            "width": 150,
        },
        {
            "fieldname": "reference_docname",
            "label": _("Reference Document"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "filters_type",
            "label": _("Type"),
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
            "fieldname": "calculated_sql",
            "label": _("Calculated SQL"),
            "fieldtype": "Data",
            "width": 500,
        },
    ]


def get_data(filters):
    """Fetch Query Filter data and calculate SQL for each"""
    
    # Get the impersonation user if specified
    impersonate_user = filters.get("impersonate_user") if filters else None
    original_user = frappe.session.user
    
    try:
        # Switch to impersonated user if specified
        if impersonate_user:
            frappe.set_user(impersonate_user)
        
        # Fetch all query filters (excluding disabled ones)
        query_filters = frappe.get_all(
            "Query Filter",
            filters={"disabled": 0},
            fields=[
                "name",
                "filter_name",
                "reference_doctype",
                "reference_report",
                "reference_docname",
                "filters_type",
                "filters",
            ],
            order_by="filter_name ASC, name ASC",
        )
        
        # Calculate SQL for each filter
        data = []
        for qf in query_filters:
            try:
                # Get the full document to calculate SQL
                filter_doc = frappe.get_doc("Query Filter", qf.name)
                calculated_sql = filter_doc.get_sql()
                # Remove line breaks from SQL
                calculated_sql = calculated_sql.replace("\n", " ").replace("\r", " ")
            except Exception as e:
                # If there's an error calculating SQL, show the error message
                calculated_sql = f"ERROR: {str(e)}"
            
            # Add calculated SQL to the row
            qf["calculated_sql"] = calculated_sql
            data.append(qf)
        
        return data
    
    finally:
        # Always switch back to the original user
        if impersonate_user and original_user:
            frappe.set_user(original_user)
