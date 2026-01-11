// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports["AC Principal Query Filters"] = {
    filters: [],
    filter_data: {},
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Format the filter_name column to show link to Query Filter
        if (column.fieldname === "filter_name" && data.query_filter) {
            const link_url = frappe.utils.get_form_link("Query Filter", data.query_filter);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        // Format the user column to show full name with link to user profile
        if (column.fieldname === "user" && data.user_id) {
            const link_url = frappe.utils.get_form_link("User", data.user_id);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        // Format the reference_docname column to show link to the referenced document
        if (column.fieldname === "reference_docname" && data.reference_doctype && data.reference_docname) {
            const link_url = frappe.utils.get_form_link(data.reference_doctype, data.reference_docname);
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`;
        }
        
        if (column.fieldname === "filters" && data.filters) {
            frappe.query_reports["AC Principal Query Filters"].filter_data[data.query_filter] = {
                filters: data.filters,
                filters_type: data.filters_type
            };
            const escaped_name = data.query_filter.replace(/'/g, "\\'");
            return `
            <button class="btn btn-default btn-xs" onclick="frappe.query_reports['AC Principal Query Filters'].show_filter_dialog('${escaped_name}')">
                View Filter
            </button>
            `;
        }
        
        return value;
    },
    "show_filter_dialog": function(name) {
        const filter_info = this.filter_data[name];
        
        if (!filter_info) {
            frappe.msgprint(__("Filter not found"));
            return;
        }
        
        // Determine the code editor language based on filter type
        let language = 'Python';
        if (filter_info.filters_type === 'SQL') {
            language = 'SQL';
        } else if (filter_info.filters_type === 'JSON') {
            language = 'JSON';
        }
        
        const dialog = new frappe.ui.Dialog({
            title: __('Filter: {0}', [name]),
            fields: [{
                fieldtype: 'Code',
                fieldname: 'filters',
                label: __('Filter ({0})', [filter_info.filters_type]),
                options: language,
                default: filter_info.filters,
            }],
            size: 'large'
        });
        
        dialog.show();
    }
};
