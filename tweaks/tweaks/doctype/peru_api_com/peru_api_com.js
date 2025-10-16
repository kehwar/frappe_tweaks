// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("PERU API COM", {
	refresh(frm) {
        frm.add_custom_button(__('Logs'), function() {
            frappe.set_route("List", "PERU API COM Log");
        });
        frm.page.add_menu_item(__('See Website'), function() {
            window.open(frm.doc.website_url, "_blank");
        });
        frm.page.add_menu_item(__('Restore Defaults'), function() {
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
