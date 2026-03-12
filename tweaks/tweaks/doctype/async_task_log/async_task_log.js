// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Async Task Log", {
	refresh(frm) {
		if (frm.doc.job_id) {
			frm.add_custom_button(__("View Job"), () => {
				frappe.set_route("Form", "RQ Job", frm.doc.job_id);
			});
		}

		if (frm.doc.status === "Pending") {
			frm.add_custom_button(__("Enqueue"), () => {
				frm.call("enqueue_execution").then(() => frm.reload_doc());
			});
		}

		if (["Queued", "Started"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel"), () => {
				frappe.confirm(__("Are you sure you want to cancel this task?"), () => {
					frm.call("cancel").then(() => frm.reload_doc());
				});
			});
		}
	},
});
