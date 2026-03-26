// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports['Form Customizations'] = {
    filters: [
        {
            fieldname: 'doctype',
            label: __('DocType'),
            fieldtype: 'Link',
            options: 'DocType',
        },
        {
            fieldname: 'customization_module',
            label: __('Customization Module'),
            fieldtype: 'Link',
            options: 'Module Def',
        },
        {
            fieldname: 'customization_type',
            label: __('Customization Type'),
            fieldtype: 'Select',
            options: [
                '',
                'Custom Field',
                'Property Setter',
            ],
        },
        {
            fieldname: 'show_system_generated',
            label: __('Show System Generated'),
            fieldtype: 'Check',
        },
        {
            fieldname: 'show_ui_fields',
            label: __('Show UI Fields'),
            fieldtype: 'Check',
        },
        {
            fieldname: 'doctype_or_field',
            label: __('Applied For'),
            fieldtype: 'Select',
            options: ['', 'DocType', 'DocField'],
        },
        {
            fieldname: 'show_custom_doctype',
            label: __('Show Custom DocType'),
            fieldtype: 'Check',
        },
    ],
    formatter: function (value, row, column, data, default_formatter) {

        if (column.fieldname === 'dt' && data && data.dt) {
            // Link to filtered list view for the DocType
            if (data.customization_type === 'Custom Field') {
                const link_url = `/app/custom-field?dt=${encodeURIComponent(data.dt)}`
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            } else if (data.customization_type === 'Property Setter') {
                const link_url = `/app/property-setter?doc_type=${encodeURIComponent(data.dt)}`
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            }
        }

        if (column.fieldname === 'customization_type' && data && data.customization_name) {
            // Link directly to the Custom Field or Property Setter document
            const doctype = data.customization_type === 'Custom Field' ? 'Custom Field' : 'Property Setter'
            const link_url = frappe.utils.get_form_link(doctype, data.customization_name)
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
        }

        if (column.fieldname === 'fieldname' && data && data.customization_name) {
            // Link directly to the document (same target as customization_type)
            const doctype = data.customization_type === 'Custom Field' ? 'Custom Field' : 'Property Setter'
            const link_url = frappe.utils.get_form_link(doctype, data.customization_name)
            return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
        }

        return default_formatter(value, row, column, data)
    },
}
