// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["Google Spreadsheet Peek"] = {
    "filters": [
        {
            "fieldname": "google_spreadsheet",
            "label": __("Google Spreadsheet"),
            "fieldtype": "Link",
            "options": "Google Spreadsheet",
            "reqd": 1
        }
    ]
};
