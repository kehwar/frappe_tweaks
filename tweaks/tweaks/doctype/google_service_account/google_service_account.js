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
                        {
                            label: 'File Type',
                            fieldname: 'file_type',
                            fieldtype: 'Select',
                            options: 'sheets\nexcel',
                            default: 'sheets',
                        },
                    ],
                    (values) => {
                        frappe.call({
                            method: 'tweaks.tweaks.doctype.google_service_account.google_service_account.get_sheet_titles',
                            args: {
                                spreadsheet_id: values.spreadsheet_id,
                                serviceaccount: frm.doc.name,
                                file_type: values.file_type,
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

            frm.add_custom_button(__('Test Data Fetch'), () => {
                frappe.prompt(
                    [
                        {
                            label: 'Spreadsheet ID',
                            fieldname: 'spreadsheet_id',
                            fieldtype: 'Data',
                            reqd: 1,
                        },
                        {
                            label: 'Sheet Name',
                            fieldname: 'sheet',
                            fieldtype: 'Data',
                            description: 'Leave blank to use first sheet',
                        },
                        {
                            label: 'Range',
                            fieldname: 'cell_range',
                            fieldtype: 'Data',
                            description: 'A1 notation (e.g., A1:C10). Leave blank for all data',
                        },
                        {
                            label: 'File Type',
                            fieldname: 'file_type',
                            fieldtype: 'Select',
                            options: 'sheets\nexcel',
                            default: 'sheets',
                        },
                    ],
                    (values) => {
                        frappe.call({
                            method: 'tweaks.tweaks.doctype.google_service_account.google_service_account.get_rows',
                            args: {
                                spreadsheet_id: values.spreadsheet_id,
                                sheet: values.sheet || null,
                                cell_range: values.cell_range || null,
                                first_row_as_headers: true,
                                serviceaccount: frm.doc.name,
                                file_type: values.file_type,
                            },
                            callback: (r) => {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __('Data Preview'),
                                        message: `Fetched ${r.message.length} rows.<br><br>First row: <pre>${JSON.stringify(r.message[0], null, 2)}</pre>`,
                                        indicator: 'green',
                                    })
                                }
                            },
                        })
                    },
                    __('Test Data Fetch'),
                    __('Fetch Data'),
                )
            })
        }
    },
})
