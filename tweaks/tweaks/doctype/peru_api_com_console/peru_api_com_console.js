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
		frm.trigger("setup_keyboard_shortcuts");
	},
	
	/**
	 * Refresh event handler for PERU API COM Console form.
	 * Orchestrates the setup of console interface components.
	 * @param {Object} frm - The form object
	 */
	refresh(frm) {
		frm.trigger("configure_form_behavior");
        frm.trigger("setup_primary_actions");
        frm.trigger("setup_navigation_buttons");
	},

	/**
	 * Sets up keyboard shortcuts for enhanced user experience.
	 * @param {Object} frm - The form object
	 */
	setup_keyboard_shortcuts(frm) {
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+enter",
			action: () => frm.page.btn_primary.trigger("click"),
			page: frm.page,
			description: __("Search"),
			ignore_inputs: true,
		});
	},

	/**
	 * Configures form behavior and settings.
	 * @param {Object} frm - The form object
	 */
	configure_form_behavior(frm) {
		// Disable save since this is a testing console
		frm.disable_save();
	},

	/**
	 * Sets up primary action buttons with loading states.
	 * @param {Object} frm - The form object
	 */
	setup_primary_actions(frm) {
		frm.page.set_primary_action(__("Search"), ($btn) => {
			$btn.text(__("Searching..."));
			return frm
				.execute_action("Search")
				.finally(() => $btn.text(__("Search")));
		});
	},

	/**
	 * Sets up navigation buttons for related functionality.
	 * @param {Object} frm - The form object
	 */
	setup_navigation_buttons(frm) {
        // Add navigation to logs
        frm.add_custom_button(__('Logs'), function() {
            frappe.set_route('List', 'PERU API COM Log');
        });

        // Add Settings menu item for configuration
        frm.page.add_menu_item(__('Settings'), function() {
            frappe.set_route("List", "PERU API COM");
        });
	}
});
