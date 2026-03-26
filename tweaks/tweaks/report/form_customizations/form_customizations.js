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
            fieldname: 'doctype_module',
            label: __('DocType Module'),
            fieldtype: 'Link',
            options: 'Module Def',
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
            label: __('System Generated'),
            fieldtype: 'Select',
            options: ['', 'Yes', 'No'],
        },
        {
            fieldname: 'show_ui_fields',
            label: __('UI Fields'),
            fieldtype: 'Select',
            options: ['', 'Yes', 'No'],
        },
        {
            fieldname: 'doctype_or_field',
            label: __('Applied For'),
            fieldtype: 'Select',
            options: ['', 'DocType', 'DocField'],
        },
        {
            fieldname: 'status',
            label: __('Status'),
            fieldtype: 'Select',
            options: ['', 'Active', 'Stale'],
        },
        {
            fieldname: 'show_custom_doctype',
            label: __('Custom DocType'),
            fieldtype: 'Select',
            options: ['', 'Yes', 'No'],
        },
    ],
    formatter: function (value, row, column, data, default_formatter) {

        if (column.fieldname === 'status' && value) {
            const color_map = {
                'Active': 'green',
                'Stale': 'orange',
            }
            const color = color_map[value] || 'gray'
            return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(value)}</span>`
        }

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

    onload(report) {
        report.page.add_inner_button(__('Bulk Migrate'), () => {
            const get_filter = (fieldname) => report.get_filter_value(fieldname) || ''

            const dialog = new frappe.ui.Dialog({
                title: __('Bulk Migrate Customizations'),
                fields: [
                    {
                        fieldtype: 'HTML',
                        options: `<div class="alert alert-info" style="margin-bottom: 12px;">
                            ${__('This will load and re-save each matching DocType to apply its customizations.')}
                        </div>`,
                    },
                    {
                        label: __('Status'),
                        fieldname: 'status',
                        fieldtype: 'Select',
                        options: '\nActive\nStale',
                        default: get_filter('status'),
                    },
                    {
                        label: __('DocType'),
                        fieldname: 'doctype',
                        fieldtype: 'Link',
                        options: 'DocType',
                        default: get_filter('doctype'),
                    },
                    {
                        label: __('Customization Module'),
                        fieldname: 'customization_module',
                        fieldtype: 'Link',
                        options: 'Module Def',
                        default: get_filter('customization_module'),
                    },
                    {
                        label: __('Customization Type'),
                        fieldname: 'customization_type',
                        fieldtype: 'Select',
                        options: '\nCustom Field\nProperty Setter',
                        default: get_filter('customization_type'),
                    },
                    {
                        label: __('Applied For'),
                        fieldname: 'doctype_or_field',
                        fieldtype: 'Select',
                        options: '\nDocType\nDocField',
                        default: get_filter('doctype_or_field'),
                    },
                    {
                        label: __('System Generated'),
                        fieldname: 'show_system_generated',
                        fieldtype: 'Select',
                        options: '\nYes\nNo',
                        default: get_filter('show_system_generated'),
                    },
                    {
                        label: __('UI Fields'),
                        fieldname: 'show_ui_fields',
                        fieldtype: 'Select',
                        options: '\nYes\nNo',
                        default: get_filter('show_ui_fields'),
                    },
                    {
                        label: __('Custom DocType'),
                        fieldname: 'show_custom_doctype',
                        fieldtype: 'Select',
                        options: '\nYes\nNo',
                        default: get_filter('show_custom_doctype'),
                    },
                ],
                primary_action_label: __('Migrate'),
                primary_action(filters) {
                    dialog.hide()
                    frappe.call({
                        method: 'tweaks.tweaks.report.form_customizations.form_customizations_actions.migrate_customizations',
                        args: { filters },
                        callback({ message }) {
                            const { migrated, failed, errors } = message
                            if (failed) {
                                const error_list = Object.entries(errors)
                                    .map(([dt, err]) => `<li><b>${frappe.utils.escape_html(dt)}</b>: ${frappe.utils.escape_html(err)}</li>`)
                                    .join('')
                                frappe.msgprint({
                                    title: __('Bulk Migrate Result'),
                                    message: __('Migrated: {0} &nbsp; Failed: {1}<ul style="margin-top:8px">{2}</ul>', [migrated, failed, error_list]),
                                    indicator: 'orange',
                                })
                            } else {
                                frappe.show_alert({
                                    message: __('Migrated {0} DocType(s)', [migrated]),
                                    indicator: 'green',
                                })
                            }
                        },
                    })
                },
            })
            dialog.show()
        }, __('Actions'))

        report.page.add_inner_button(__('Bulk Delete'), () => {
            const get_filter = (fieldname) => report.get_filter_value(fieldname) || ''

            const dialog = new frappe.ui.Dialog({
                title: __('Bulk Delete Customizations'),
                fields: [
                    {
                        fieldtype: 'HTML',
                        options: `<div class="alert alert-warning" style="margin-bottom: 12px;">
                            ${__('This will <b>permanently delete</b> all matching Custom Fields and Property Setters.')}
                        </div>`,
                    },
                    {
                        label: __('Status'),
                        fieldname: 'status',
                        fieldtype: 'Select',
                        options: '\nActive\nStale',
                        default: get_filter('status'),
                    },
                    {
                        label: __('DocType'),
                        fieldname: 'doctype',
                        fieldtype: 'Link',
                        options: 'DocType',
                        default: get_filter('doctype'),
                    },
                    {
                        label: __('Customization Module'),
                        fieldname: 'customization_module',
                        fieldtype: 'Link',
                        options: 'Module Def',
                        default: get_filter('customization_module'),
                    },
                    {
                        label: __('Customization Type'),
                        fieldname: 'customization_type',
                        fieldtype: 'Select',
                        options: '\nCustom Field\nProperty Setter',
                        default: get_filter('customization_type'),
                    },
                    {
                        label: __('Applied For'),
                        fieldname: 'doctype_or_field',
                        fieldtype: 'Select',
                        options: '\nDocType\nDocField',
                        default: get_filter('doctype_or_field'),
                    },
                    {
                        label: __('System Generated'),
                        fieldname: 'show_system_generated',
                        fieldtype: 'Select',
                        options: '\nYes\nNo',
                        default: get_filter('show_system_generated'),
                    },
                    {
                        label: __('UI Fields'),
                        fieldname: 'show_ui_fields',
                        fieldtype: 'Select',
                        options: '\nYes\nNo',
                        default: get_filter('show_ui_fields'),
                    },
                    {
                        label: __('Custom DocType'),
                        fieldname: 'show_custom_doctype',
                        fieldtype: 'Select',
                        options: '\nYes\nNo',
                        default: get_filter('show_custom_doctype'),
                    },
                ],
                primary_action_label: __('Delete'),
                primary_action(filters) {
                    dialog.hide()
                    frappe.call({
                        method: 'tweaks.tweaks.report.form_customizations.form_customizations_actions.enqueue_delete_customizations',
                        args: { filters },
                        callback({ message: task_name }) {
                            frappe.show_alert({
                                message: __('Task enqueued: {0}', [task_name]),
                                indicator: 'green',
                            })
                        },
                    })
                },
            })
            dialog.show()
        }, __("Actions"))
    },
}
