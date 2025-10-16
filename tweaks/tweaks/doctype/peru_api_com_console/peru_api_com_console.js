// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

/**
 * Form script for PERU API COM Console doctype.
 * Provides testing interface for Peru API services with keyboard shortcuts and search functionality.
 */
frappe.ui.form.on("PERU API COM Console", {
    /**
     * Onload event handler for PERU API COM Console form.
     * Sets up keyboard shortcuts for quick search functionality.
     * @param {Object} frm - The form object
     */
    onload: function (frm) {
		// Add Ctrl+Enter keyboard shortcut for quick search
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+enter",
			action: () => frm.page.btn_primary.trigger("click"),
			page: frm.page,
			description: __("Search"),
			ignore_inputs: true,
		});
	},
	
	/**
	 * Refresh event handler for PERU API COM Console form.
	 * Sets up primary search action button and navigation links.
	 * @param {Object} frm - The form object
	 */
	refresh(frm) {
		// Disable save since this is a testing console
		frm.disable_save();
		
		// Set up primary search action with loading state
		frm.page.set_primary_action(__("Search"), ($btn) => {
			$btn.text(__("Searching..."));
			return frm
				.execute_action("Search")
				.finally(() => $btn.text(__("Search")));
		});
		
		// Add navigation button to view logs
        frm.add_custom_button(__('Logs'), function() {
            frappe.set_route('List', 'PERU API COM Log');
        });
	},
});
