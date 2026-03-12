// Copyright (c) 2026, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings["Async Task Log"] = {
	refresh(listview) {
		show_toggle_dispatcher_button(listview);
	},
};

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
