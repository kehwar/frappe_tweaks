// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("PERU API COM Console", {
    onload: function (frm) {
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+enter",
			action: () => frm.page.btn_primary.trigger("click"),
			page: frm.page,
			description: __("Search"),
			ignore_inputs: true,
		});
	},
	refresh(frm) {
		frm.disable_save();
		frm.page.set_primary_action(__("Search"), ($btn) => {
			$btn.text(__("Searching..."));
			return frm
				.execute_action("Search")
				.finally(() => $btn.text(__("Search")));
		});
        frm.add_custom_button(__('Logs'), function() {
            frappe.set_route('List', 'PERU API COM Log');
        });
	},
});
