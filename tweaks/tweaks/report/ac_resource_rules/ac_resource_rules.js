// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["AC Resource Rules"] = {
    "filters": [
        {
            "fieldname": "resource",
            "label": __("Resource"),
            "fieldtype": "Link",
            "options": "AC Resource",
            "reqd": 1
        },
        {
            "fieldname": "query_filter",
            "label": __("User Filter"),
            "fieldtype": "Link",
            "options": "Query Filter",
            "reqd": 0,
            "get_query": function() {
                return {
                    filters: {
                        "reference_doctype": ["in", ["User", "User Group", "Role", "Role Profile"]]
                    }
                };
            }
        },
        {
            "fieldname": "action",
            "label": __("Action"),
            "fieldtype": "Link",
            "options": "AC Action",
            "reqd": 0,
            "description": __("Filter by specific action. When specified, cells show Y/N instead of listing all actions.")
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        // Format the user column to show full name but link to user profile
        if (column.fieldname === "user" && data.full_name) {
            return `<a href="/app/user/${encodeURIComponent(value)}">${frappe.utils.escape_html(data.full_name)}</a>`;
        }
        return default_formatter(value, row, column, data);
    }
};
