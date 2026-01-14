// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.query_reports['Customizations'] = {
    filters: [
        {
            fieldname: 'doctype',
            label: __('DocType'),
            fieldtype: 'Link',
            options: 'DocType',
        },
        {
            fieldname: 'module',
            label: __('Module'),
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
    ],
    formatter: function (value, row, column, data, default_formatter) {

        if (column.fieldname === 'dt' && data && data.dt) {
            // Link to Custom Field or Property Setter list filtered by DocType
            if (data.customization_type === 'Custom Field') {
                const link_url = `/app/custom-field?dt=${encodeURIComponent(data.dt)}`
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            } else if (data.customization_type === 'Property Setter') {
                const link_url = `/app/property-setter?doc_type=${encodeURIComponent(data.dt)}`
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            }
        }

        if (column.fieldname === 'fieldname' && data) {
            if (data.customization_type === 'Custom Field' && data.custom_field_name) {
                // Link to the Custom Field document using the name from the report
                const link_url = frappe.utils.get_form_link('Custom Field', data.custom_field_name)
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            } else if (data.customization_type === 'Property Setter') {
                // Link to Property Setter list filtered by doc_type, doctype_or_field, and field_name
                let link_url = `/app/property-setter?doc_type=${encodeURIComponent(data.dt)}`
                
                // Add doctype_or_field filter if available
                if (data.doctype_or_field) {
                    link_url += `&doctype_or_field=${encodeURIComponent(data.doctype_or_field)}`
                }
                
                // Check if this is a field-level property setter (contains ' / ')
                if (data.fieldname && data.fieldname.includes(' / ')) {
                    const field_name = data.fieldname.split(' / ')[1]
                    if (field_name && field_name !== data.dt) {
                        link_url += `&field_name=${encodeURIComponent(field_name)}`
                    }
                }
                
                return `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            }
        }

        return default_formatter(value, row, column, data)
    },
}
