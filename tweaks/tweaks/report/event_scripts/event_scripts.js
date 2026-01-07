// Copyright (c) 2026, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["Event Scripts"] = {
    scripts: {},
    parameters: {},
    "filters": [
        {
            "fieldname": "document_type",
            "label": __("Document Type"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 100
        },
        {
            "fieldname": "document_type_group",
            "label": __("Document Type Group"),
            "fieldtype": "Link",
            "options": "DocType Group",
            "width": 100
        },
        {
            "fieldname": "doctype_event",
            "label": __("Event"),
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
            ],
            "default": ""
        },
        {
            "fieldname": "action",
            "label": __("Action"),
            "fieldtype": "Select",
            "options": [
                "",
                "*",
                "read",
                "write"
            ],
            "default": ""
        }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Refresh"), () => {
            report.refresh();
        });
    },
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "script" && data.script) {
            frappe.query_reports["Event Scripts"].scripts[data.name] = data.script;
            const escaped_name = data.name.replace(/'/g, "\\'");
            return `
            <button class="btn btn-default btn-xs" onclick="frappe.query_reports['Event Scripts'].show_script_dialog('${escaped_name}')">
                View Script
            </button>
            `;
        }
        
        if (column.fieldname === "parameters" && data.parameters) {
            frappe.query_reports["Event Scripts"].parameters[data.name] = data.parameters;
            const escaped_name = data.name.replace(/'/g, "\\'");
            return `
            <button class="btn btn-default btn-xs" onclick="frappe.query_reports['Event Scripts'].show_parameters_dialog('${escaped_name}')">
                View Parameters
            </button>
            `;
        }
        
        return value;
    },
    "show_script_dialog": function(name) {
        const script = this.scripts[name];
        
        if (!script) {
            frappe.msgprint(__("Script not found"));
            return;
        }
        
        const dialog = new frappe.ui.Dialog({
            title: __('Script: {0}', [name]),
            fields: [{
                fieldtype: 'Code',
                fieldname: 'script',
                label: __('Script'),
                options: 'Python',
                default: script,
            }],
            size: 'large'
        });
        
        dialog.show();
    },
    "show_parameters_dialog": function(name) {
        const parameters = this.parameters[name];
        
        if (!parameters) {
            frappe.msgprint(__("Parameters not found"));
            return;
        }
        
        const dialog = new frappe.ui.Dialog({
            title: __('Parameters: {0}', [name]),
            fields: [{
                fieldtype: 'Code',
                fieldname: 'parameters',
                label: __('Parameters'),
                options: 'JSON',
                default: JSON.stringify(parameters, null, 4),
            }],
            size: 'large'
        });
        
        dialog.show();
    }
};
