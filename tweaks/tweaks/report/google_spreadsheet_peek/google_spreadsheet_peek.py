# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe

from tweaks.tweaks.doctype.google_service_account.google_service_account import (
    get_default_account,
)


def execute(filters=None):
    """Fetch data from a Google Spreadsheet document"""
    columns = []
    data = []

    # Validate required filter
    if not filters or not filters.get("google_spreadsheet"):
        frappe.msgprint("Please select a Google Spreadsheet document.")
        return columns, data

    try:
        # Get the Google Spreadsheet document
        spreadsheet_doc = frappe.get_doc(
            "Google Spreadsheet", filters.get("google_spreadsheet")
        )

        if not spreadsheet_doc.spreadsheet_id:
            frappe.throw(
                "Spreadsheet ID is required in the Google Spreadsheet document."
            )

        # Get the default Google Service Account
        account = get_default_account()

        # Create service based on the type
        if spreadsheet_doc.type == "Excel":
            service = account.get_excel_service(spreadsheet_doc.spreadsheet_id)
        else:
            # Default to Sheet type
            service = account.get_sheets_service(spreadsheet_doc.spreadsheet_id)

        # Get the rows using first row as headers
        rows = service.get_rows(
            sheet=spreadsheet_doc.sheet_title or None, first_row_as_headers=True
        )

        if not rows:
            return columns, data

        # Extract columns from first row keys
        if len(rows) > 0:
            headers = list(rows[0].keys())
            columns = [
                {
                    "label": header,
                    "fieldname": header,
                    "fieldtype": "Data",
                    "width": 150,
                }
                for header in headers
            ]

        data = rows

    except Exception as e:
        frappe.log_error(f"Error fetching Google Sheets data: {str(e)}")
        frappe.throw(f"Failed to fetch data from Google Sheets: {str(e)}")

    return columns, data
