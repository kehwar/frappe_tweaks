// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("PERU API COM", {
	refresh(frm) {
        frm.add_custom_button(__('Logs'), function() {
            frappe.set_route("List", "PERU API COM Log");
        });
	},
});
