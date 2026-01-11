// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["Query Filters"] = {
    filters_data: {},
    "onload": function(report) {
        report.page.add_inner_button(__("Refresh"), () => {
            report.refresh();
        });
    },
    "formatter": function(value, row, column, data, default_formatter) {
        // Format the filter_name column to show link to Query Filter document
        if (column.fieldname === "filter_name" && data.name) {
            const link_url = frappe.utils.get_form_link("Query Filter", data.name);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        // Format the reference column to show proper link based on reference_type
        if (column.fieldname === "reference" && value && data.reference_type) {
            if (data.reference_type === "Report") {
                const link_url = `/app/query-report/${encodeURIComponent(value)}`;
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
            } else if (data.reference_type === "DocType") {
                const link_url = `/app/${frappe.router.slug(value)}`;
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
            }
        }
        
        // Format the reference_docname column to show proper link
        if (column.fieldname === "reference_docname" && value && data.reference_doctype) {
            const link_url = frappe.utils.get_form_link(data.reference_doctype, value);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        value = default_formatter(value, row, column, data);
        
        if (column.fieldname === "filters" && data.filters) {
            frappe.query_reports["Query Filters"].filters_data[data.name] = data.filters;
            const escaped_name = data.name.replace(/'/g, "\\'");
            return `
            <button class="btn btn-default btn-xs" onclick="frappe.query_reports['Query Filters'].show_filter_dialog('${escaped_name}')">
                View Filter
            </button>
            `;
        }
        
        return value;
    },
    "show_filter_dialog": function(name) {
        const filters = this.filters_data[name];
        
        if (!filters) {
            frappe.msgprint(__("Filter not found"));
            return;
        }
        
        const dialog = new frappe.ui.Dialog({
            title: __('Filter: {0}', [name]),
            fields: [{
                fieldtype: 'Code',
                fieldname: 'filters',
                label: __('Filter'),
                options: 'Python',
                default: filters,
            }],
            size: 'large'
        });
        
        dialog.show();
    }
};
