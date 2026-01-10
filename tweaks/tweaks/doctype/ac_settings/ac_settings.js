// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Settings", {
    refresh(frm) {
        // Nothing to do on refresh
    },
    
    clear_cache_button(frm) {
        frappe.call({
            method: "tweaks.tweaks.doctype.ac_settings.ac_settings.clear_ac_cache",
            callback: function(r) {
                if (!r.exc) {
                    frappe.show_alert({
                        message: __("AC Rule cache cleared successfully"),
                        indicator: "green"
                    });
                }
            }
        });
    }
});
