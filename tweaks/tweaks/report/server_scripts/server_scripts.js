// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["Server Scripts"] = {
    scripts_data: {},
    "filters": [
        {
            "fieldname": "script_type",
            "label": __("Script Type"),
            "fieldtype": "Select",
            "options": ["\n", "DocType Event", "Scheduler Event", "Permission Query", "API"],
            "reqd": 0
        },
        {
            "fieldname": "reference_doctype",
            "label": __("Reference DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "reqd": 0
        },
        {
            "fieldname": "doctype_event",
            "label": __("DocType Event"),
            "fieldtype": "Select",
            "options": ["\n", "Before Naming", "Before Insert", "Before Validate", "Before Save", "After Validate", "After Insert", "After Save", "Before Rename", "After Rename", "Before Submit", "After Submit", "Before Cancel", "After Cancel", "Before Delete", "After Delete", "Before Save (Submitted Document)", "After Save (Submitted Document)", "Before Print", "On Payment Authorization", "Before Change", "After Change", "Before Export", "Before Import", "Before Workflow Transition", "After Workflow Transition"],
            "reqd": 0
        }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Refresh"), () => {
            report.refresh();
        });
    },
    "formatter": function(value, row, column, data, default_formatter) {
        // Format the title column to show link to Server Script document
        if (column.fieldname === "title" && data.name) {
            const link_url = frappe.utils.get_form_link("Server Script", data.name);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        // Format the reference_doctype column to show proper link
        if (column.fieldname === "reference_doctype" && value) {
            const link_url = `/app/${frappe.router.slug(value)}`;
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "script" && data.script) {
            frappe.query_reports["Server Scripts"].scripts_data[data.name] = data.script;
            const escaped_name = data.name.replace(/'/g, "\\'");
            return `
            <button class="btn btn-default btn-xs" onclick="frappe.query_reports['Server Scripts'].show_script_dialog('${escaped_name}')">
                View Script
            </button>
            `;
        }
        
        return value;
    },
    "show_script_dialog": function(name) {
        const script = this.scripts_data[name];
        
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
    }
};
