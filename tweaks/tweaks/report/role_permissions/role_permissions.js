// Copyright (c) 2026, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["Role Permissions"] = {
    "filters": [
        {
            "fieldname": "doctype",
            "label": __("DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "reqd": 0
        },
        {
            "fieldname": "role",
            "label": __("Role"),
            "fieldtype": "Link",
            "options": "Role",
            "reqd": 0
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nDefault\nCustom",
            "reqd": 0
        },
        {
            "fieldname": "doctype_type",
            "label": __("DocType Type"),
            "fieldtype": "Select",
            "options": "\nStandard\nCustom\nVirtual",
            "reqd": 0
        },
        {
            "fieldname": "module",
            "label": __("Module"),
            "fieldtype": "Link",
            "options": "Module Def",
            "reqd": 0
        }
    ],
};
