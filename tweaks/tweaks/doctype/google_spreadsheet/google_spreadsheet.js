// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Google Spreadsheet", {
    refresh(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("View Spreadsheet"), () => {
                frappe.set_route("query-report", "Google Spreadsheet Peek", {
                    google_spreadsheet: frm.doc.name
                })
            })
        }
    },
})
