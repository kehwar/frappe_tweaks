// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

/**
 * Form script for PERU API COM doctype.
 * Provides UI interactions and configuration management for Peru API services.
 */
frappe.ui.form.on("PERU API COM", {
	/**
	 * Refresh event handler for PERU API COM form.
	 * Sets up custom buttons, menu items, and initializes form with default values.
	 * @param {Object} frm - The form object
	 */
	refresh(frm) {
        // Add Console button to navigate to testing interface
        frm.add_custom_button(__('Console'), function() {
            frappe.set_route('Form', 'PERU API COM Console');
        });
        
        // Add menu items for navigation and actions
        frm.page.add_menu_item(__('Logs'), function() {
            frappe.set_route("List", "PERU API COM Log");
        });
        frm.page.add_menu_item(__('See Website'), function() {
            window.open(frm.doc.website_url, "_blank");
        });
        frm.page.add_menu_item(__('Restore Defaults'), function() {
            // Restore default configuration values
            frappe.call({
                method: "tweaks.tweaks.doctype.peru_api_com.peru_api_com.restore_defaults",
                args: {
                    name: frm.doc.name
                },
                callback: function(r) {
                    if(!r.exc) {
                        frm.reload_doc();
                    }
                }
            });
        });
        
        // Auto-populate empty fields with default values on form load
        frappe.call({
            "method": "tweaks.tweaks.doctype.peru_api_com.peru_api_com.get_default_settings",
            callback: function(r) {
                if(r.message) {
                    const defaults = r.message;
                    let changed = false;
                    if (!frm.doc.website_url){
                        frm.set_value("website_url", defaults.website_url);
                        changed = true;
                    }
                    if (!frm.doc.ruc_url){
                        frm.set_value("ruc_url", defaults.ruc_url);
                        changed = true;
                    }
                    if (!frm.doc.dni_url){
                        frm.set_value("dni_url", defaults.dni_url);
                        changed = true;
                    }
                    if (!frm.doc.tc_url){
                        frm.set_value("tc_url", defaults.tc_url);
                        changed = true;
                    }
                    if (!frm.doc.auth_header){
                        frm.set_value("auth_header", defaults.auth_header);
                        changed = true;
                    }
                    if (changed) {
                        frm.save();
                    }
                }
            }
        })
	},
});
