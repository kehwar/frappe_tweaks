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
        }
    ],
};
