// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["AC Rules"] = {
    "filters": [
        {
            "fieldname": "action",
            "label": __("Action"),
            "fieldtype": "Link",
            "options": "AC Action",
            "reqd": 0,
            "description": __("Filter by specific action. Shows Y/N instead of listing all actions.")
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "resource" && data && data.resource_name) {
            return `<a href="/app/ac-resource/${encodeURIComponent(data.resource_name)}">${value}</a>`;
        }
        
        if (column.fieldname === "user" && data && data.user_id) {
            return `<a href="/app/user/${encodeURIComponent(data.user_id)}">${value}</a>`;
        }
        
        return value;
    }
};
