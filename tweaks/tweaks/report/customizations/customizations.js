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
}
