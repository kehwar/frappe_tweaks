// Copyright (c) 2025, and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sync Job', {
    refresh(frm) {
        // Add Start button for pending jobs
        if (frm.doc.status === 'Pending') {
            frm.add_custom_button(__('Start'), () => {
                frappe.call({
                    method: 'start',
                    doc: frm.doc,
                    callback: (r) => {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Sync job queued'),
                                indicator: 'blue',
                            })
                            frm.reload_doc()
                        }
                    },
                })
            })
        }

        // Add Cancel button
        if (frm.doc.status === 'Pending' || frm.doc.status === 'Queued' || frm.doc.status === 'Failed') {
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
    },
})

function get_status_color(status) {
    const colors = {
        'Pending': 'gray',
        'Queued': 'blue',
        'Started': 'orange',
        'Finished': 'green',
        'Failed': 'red',
        'Canceled': 'gray',
        'Skipped': 'gray',
    }
    return colors[status] || 'gray'
}
