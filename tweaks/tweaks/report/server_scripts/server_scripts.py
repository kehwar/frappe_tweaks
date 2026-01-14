# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    """
    Server Scripts Report

    Lists all Server Script documents with their configuration and script content.
    Useful for reviewing and managing server-side automation scripts.

    Filters:
        script_type (optional): Filter by script type (DocType Event, Scheduler Event, Permission Query, API)
        reference_doctype (optional): Filter by reference DocType

    Columns:
        - Name: Link to the Server Script document
        - Title: Human-readable title of the script
        - Script Type: Type of script (DocType Event, Scheduler Event, Permission Query, or API)
        - Reference DocType: The DocType this script applies to (for DocType Event and Permission Query types)
        - DocType Event: The specific event that triggers the script (for DocType Event type)
        - Event Frequency: How often the script runs (for Scheduler Event type)
        - API Method: The API method name (for API type)
        - Module: The module this script belongs to
        - Disabled: Whether the script is disabled
        - Script: The Python script code (click "View Script" button to see in dialog)

    Features:
        - Filter by script type or reference doctype
        - Script column includes "View Script" button to display code in dialog
        - Clickable links to open Server Script documents and reference doctypes
        - Shows all Server Scripts (both enabled and disabled)

    Permissions:
        Requires System Manager role

    Related:
        - Server Script DocType: frappe/core/doctype/server_script/
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
            "options": "Server Script",
            "width": 180,
            "hidden": 1,
        },
        {
            "fieldname": "title",
            "label": _("Title"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "script_type",
            "label": _("Script Type"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "reference_doctype",
            "label": _("Reference DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 150,
        },
        {
            "fieldname": "doctype_event",
            "label": _("DocType Event"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "event_frequency",
            "label": _("Event Frequency"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "api_method",
            "label": _("API Method"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "module",
            "label": _("Module"),
            "fieldtype": "Link",
            "options": "Module Def",
            "width": 120,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "script",
            "label": _("Script"),
            "fieldtype": "Code",
            "width": 120,
        },
    ]


def get_data(filters):
    """Fetch Server Script data with filters applied"""
    conditions = get_conditions(filters)

    server_scripts = frappe.get_all(
        "Server Script",
        fields=[
            "name",
            "title",
            "script_type",
            "reference_doctype",
            "doctype_event",
            "event_frequency",
            "api_method",
            "module",
            "disabled",
            "script",
        ],
        filters=conditions,
        order_by="disabled asc, script_type asc, title asc",
    )

    # Add status field based on disabled flag
    # If module is not set, get it from reference doctype
    for script in server_scripts:
        script["status"] = "Disabled" if script.get("disabled") else "Enabled"

        if not script.get("module") and script.get("reference_doctype"):
            try:
                doctype_module = frappe.db.get_value(
                    "DocType", script.get("reference_doctype"), "module"
                )
                if doctype_module:
                    script["module"] = doctype_module
            except Exception:
                pass

    return server_scripts


def get_conditions(filters):
    """Build filter conditions from report filters"""
    conditions = {}

    # Filter by script type if specified
    if filters.get("script_type"):
        conditions["script_type"] = filters.get("script_type")

    # Filter by reference doctype if specified
    if filters.get("reference_doctype"):
        conditions["reference_doctype"] = filters.get("reference_doctype")

    return conditions
