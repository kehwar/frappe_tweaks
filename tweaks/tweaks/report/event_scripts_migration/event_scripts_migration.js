// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["Event Scripts Migration"] = {
    "filters": [
        {
            "fieldname": "disabled",
            "label": __("Disabled"),
            "fieldtype": "Select",
            "options": ["", "0", "1"],
            "default": ""
        },
        {
            "fieldname": "document_type",
            "label": __("Document Type"),
            "fieldtype": "Link",
            "options": "DocType"
        },
        {
            "fieldname": "doctype_event",
            "label": __("DocType Event"),
            "fieldtype": "Select",
            "options": [
                "",
                "after_delete",
                "after_insert",
                "after_rename",
                "after_transition",
                "autoname",
                "before_cancel",
                "before_insert",
                "before_naming",
                "before_rename",
                "before_save",
                "before_submit",
                "before_transition",
                "before_update_after_submit",
                "before_validate",
                "db_insert",
                "db_update",
                "has_field_permission",
                "has_permission",
                "on_cancel",
                "on_change",
                "on_change_or_rename",
                "on_submit",
                "on_trash",
                "on_update",
                "on_update_after_submit",
                "transition_condition",
                "validate"
            ]
        },
        {
            "fieldname": "migration_target",
            "label": __("Migration Target"),
            "fieldtype": "Select",
            "options": [
                "",
                "Server Script",
                "AC Rule",
                "Server Script or AC Rule"
            ]
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Highlight disabled scripts
        if (column.fieldname == "disabled" && data.disabled == 1) {
            value = `<span style="color: red;">${value}</span>`;
        }
        
        // Color-code migration targets
        if (column.fieldname == "migration_target") {
            if (data.migration_target == "AC Rule") {
                value = `<span style="color: blue; font-weight: bold;">${value}</span>`;
            } else if (data.migration_target == "Server Script") {
                value = `<span style="color: green; font-weight: bold;">${value}</span>`;
            } else if (data.migration_target && data.migration_target.includes("or")) {
                value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
            }
        }
        
        return value;
    }
};
