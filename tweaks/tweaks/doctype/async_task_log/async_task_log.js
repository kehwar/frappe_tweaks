// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Async Task Log", {
	refresh(frm) {
		frm.disable_save();

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

		if (["Pending", "Paused"].includes(frm.doc.status)) {
			const label = frm.doc.status === "Pending" ? __("Pause") : __("Resume");
			frm.add_custom_button(label, () => {
				frm.call("toggle_pause").then(() => frm.reload_doc());
			});
		}

		if (["Pending", "Paused", "Queued", "Started"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Cancel"), () => {
				const d = new frappe.ui.Dialog({
					title: __("Cancel Task"),
					fields: [
						{
							fieldtype: "Data",
							fieldname: "message",
							label: __("Message"),
							description: __("Optional reason or note for canceling this task"),
						},
					],
					primary_action_label: __("Cancel Task"),
					primary_action({ message }) {
						d.hide();
						frm.call("cancel", { message: message || null }).then(() =>
							frm.reload_doc()
						);
					},
				});
				d.show();
			});
		}

		if (["Failed", "Canceled"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Retry"), () => {
				frm.call("retry", {"now": 1}).then(() => frm.reload_doc());
			});
		}
	},
});
