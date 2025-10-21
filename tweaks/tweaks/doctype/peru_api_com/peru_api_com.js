// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

/**
 * Form script for PERU API COM doctype.
 * Provides UI interactions and configuration management for Peru API services.
 */
frappe.ui.form.on("PERU API COM", {
	/**
	 * Refresh event handler for PERU API COM form.
	 * Orchestrates the setup of UI components and initialization.
	 * @param {Object} frm - The form object
	 */
	refresh(frm) {
		frm.trigger("setup_action_buttons");
        frm.trigger("setup_menu_items");
        frm.trigger("initialize_default_values");
	},

	/**
	 * Sets up action buttons in the form toolbar.
	 * @param {Object} frm - The form object
	 */
	setup_action_buttons(frm) {
		// Add Console button to navigate to testing interface
		frm.add_custom_button(__('Console'), function() {
			frappe.set_route('Form', 'PERU API COM Console');
		});
	},

	/**
	 * Sets up menu items for navigation and administrative actions.
	 * @param {Object} frm - The form object
	 */
	setup_menu_items(frm) {
		// Add navigation menu items
		frm.page.add_menu_item(__('Logs'), function() {
			frappe.set_route("List", "PERU API COM Log");
		});
		
		frm.page.add_menu_item(__('See Website'), function() {
			window.open(frm.doc.website_url, "_blank");
		});
		
		// Add administrative actions
		frm.page.add_menu_item(__('Restore Defaults'), function() {
			frm.trigger("restore_default_configuration");
		});
	},

	/**
	 * Initializes form with default values for empty fields.
	 * @param {Object} frm - The form object
	 */
	initialize_default_values(frm) {
		frappe.call({
			"method": "tweaks.tweaks.doctype.peru_api_com.peru_api_com.get_default_settings",
			callback: function(r) {
				if (r.message) {
					frm.doc.defaults = r.message;
                    frm.trigger("populate_empty_fields");
				}
			}
		});
	},

	/**
	 * Restores default configuration values.
	 * @param {Object} frm - The form object
	 */
	restore_default_configuration(frm) {
		frappe.call({
			method: "tweaks.tweaks.doctype.peru_api_com.peru_api_com.restore_defaults",
			args: {
				name: frm.doc.name
			},
			callback: function(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			}
		});
	},

	/**
	 * Populates empty fields with default values and saves if changes were made.
	 * @param {Object} frm - The form object
	 * @param {Object} defaults - Default values object
	 */
	populate_empty_fields(frm) {
		let changed = false;
		
		const fields = [
			'website_url', 'ruc_url', 'ruc_suc_url', 'dni_url', 'tc_url', 'auth_header'
		];
		
		fields.forEach(field => {
			if (!frm.doc[field] && frm.doc.defaults[field]) {
				frm.set_value(field, frm.doc.defaults[field]);
				changed = true;
			}
		});
		
		if (changed) {
			frm.save();
		}
	}
});
