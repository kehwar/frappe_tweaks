// Copyright (c) 2026, and contributors
// For license information, please see license.txt

frappe.ui.form.on('Google Service Account', {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('Test Connection'), () => {
                frappe.prompt(
                    [
                        {
                            label: 'Spreadsheet ID',
                            fieldname: 'spreadsheet_id',
                            fieldtype: 'Data',
                            reqd: 1,
                        },
                    ],
                    (values) => {
                        frappe.call({
                            method: 'tweaks.tweaks.doctype.google_service_account.google_service_account.get_sheet_titles',
                            args: {
                                spreadsheet_id: values.spreadsheet_id,
                                serviceaccount: frm.doc.name,
                            },
                            callback: (r) => {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __('Sheet Titles'),
                                        message: r.message.join('<br>'),
                                        indicator: 'green',
                                    })
                                }
                            },
                        })
                    },
                    __('Test Google Sheets Connection'),
                    __('Fetch Sheets'),
                )
            })
        }
    },
})
