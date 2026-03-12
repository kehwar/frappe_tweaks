// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Async Task Log"] = {
	onload(listview) {
		add_bulk_action_buttons(listview);
	},
	refresh(listview) {
		show_toggle_dispatcher_button(listview);
	},
};

const BULK_ACTION_METHOD =
	"tweaks.tweaks.doctype.async_task_log.async_task_log_client.bulk_action";

function add_bulk_action_buttons(listview) {
	const call_bulk = async (action, data) => {
		const docnames = listview.get_checked_items(true);
		if (!docnames.length) return;
		await frappe.xcall(BULK_ACTION_METHOD, { docnames, action, data });
		listview.clear_checked_items();
		listview.refresh();
	};

	listview.page.add_action_item(__("Enqueue"), () => call_bulk("enqueue"));
	listview.page.add_action_item(__("Pause"), () => call_bulk("pause"));
	listview.page.add_action_item(__("Resume"), () => call_bulk("resume"));

	listview.page.add_action_item(__("Cancel"), () => {
		const docnames = listview.get_checked_items(true);
		if (!docnames.length) return;
		const d = new frappe.ui.Dialog({
			title: __("Cancel Tasks"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "message",
					label: __("Message"),
					description: __("Optional reason or note for canceling these tasks"),
				},
			],
			primary_action_label: __("Cancel Tasks"),
			async primary_action({ message }) {
				d.hide();
				await frappe.xcall(BULK_ACTION_METHOD, {
					docnames,
					action: "cancel",
					data: message ? { message } : null,
				});
				listview.clear_checked_items();
				listview.refresh();
			},
		});
		d.show();
	});

	listview.page.add_action_item(__("Retry"), () => call_bulk("retry"));
}

function show_toggle_dispatcher_button(list_view) {
	if (!has_common(frappe.user_roles, ["Administrator", "System Manager"])) return;

	const suspended = cint(frappe.sys_defaults.suspend_async_task_dispatch);
	const label = suspended ? __("Resume Dispatcher") : __("Suspend Dispatcher");

	list_view.page.add_inner_button(label, async () => {
		await frappe.xcall(
			"tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch.toggle_dispatcher",
			// enable if currently suspended
			{ enable: suspended }
		);

		frappe.sys_defaults.suspend_async_task_dispatch = suspended ? 0 : 1;

		list_view.page.remove_inner_button(label);
		show_toggle_dispatcher_button(list_view);
	});
}

