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
    ],
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data)

        if (column.fieldname === 'fieldname' && data) {
            if (data.customization_type === 'Custom Field' && data.custom_field_name) {
                // Link to the Custom Field document using the name from the report
                const link_url = frappe.utils.get_form_link('Custom Field', data.custom_field_name)
                value = `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
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
                
                value = `<a href="${link_url}">${frappe.utils.escape_html(value)}</a>`
            }
        }

        return value
    },
}
