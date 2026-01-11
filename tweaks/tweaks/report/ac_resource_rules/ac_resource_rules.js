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
            "label": __("Principal Filter"),
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
        },
        {
            "fieldname": "pivot",
            "label": __("Pivot"),
            "fieldtype": "Check",
            "default": 0,
            "description": __("Pivot resource query filters to columns (matrix view). Uncheck for flat table view.")
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        // Format the user column to show full name with link to user profile
        if (column.fieldname === "user" && data.user_id) {
            const link_url = frappe.utils.get_form_link("User", data.user_id);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        // Hide "N" values for better visual clarity (only show "Y" for granted access)
        if (value === "N") {
            return "";
        }
        return default_formatter(value, row, column, data);
    }
};
