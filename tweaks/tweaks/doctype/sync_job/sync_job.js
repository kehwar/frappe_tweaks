// Copyright (c) 2025, and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sync Job', {
    refresh(frm) {
        // Add Cancel button
        if (frm.doc.status === 'Queued' || frm.doc.status === 'Failed') {
            frm.add_custom_button(__('Cancel'), () => {
                frappe.prompt(
                    {
                        fieldname: 'reason',
                        fieldtype: 'Small Text',
                        label: __('Reason'),
                        reqd: false,
                    },
                    (values) => {
                        frappe.call({
                            method: 'cancel_sync',
                            doc: frm.doc,
                            args: {
                                reason: values.reason,
                            },
                            callback: (r) => {
                                if (!r.exc) {
                                    frappe.show_alert({
                                        message: __('Sync job canceled'),
                                        indicator: 'orange',
                                    })
                                    frm.reload_doc()
                                }
                            },
                        })
                    },
                    __('Cancel Sync Job'),
                    __('Cancel'),
                )
            })
        }

        // Add Retry button
        if (frm.doc.status === 'Failed') {
            frm.add_custom_button(__('Retry'), () => {
                frappe.call({
                    method: 'retry',
                    doc: frm.doc,
                    callback: (r) => {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Sync job queued for retry'),
                                indicator: 'blue',
                            })
                            frm.reload_doc()
                        }
                    },
                })
            })
        }

        // Set indicator colors
        frm.page.set_indicator(__('Status: {0}', [frm.doc.status]), get_status_color(frm.doc.status))

        // Make fields read-only after insert
        if (!frm.is_new()) {
            frm.set_df_property('sync_job_type', 'read_only', 1)
            frm.set_df_property('source_doctype', 'read_only', 1)
            frm.set_df_property('source_document_name', 'read_only', 1)
            frm.set_df_property('target_doctype', 'read_only', 1)
            frm.set_df_property('target_document_name', 'read_only', 1)
            frm.set_df_property('operation', 'read_only', 1)
            frm.set_df_property('context', 'read_only', 1)
        }
    },
})

function get_status_color(status) {
    const colors = {
        'Queued': 'blue',
        'Started': 'orange',
        'Finished': 'green',
        'Failed': 'red',
        'Canceled': 'gray',
    }
    return colors[status] || 'gray'
}
