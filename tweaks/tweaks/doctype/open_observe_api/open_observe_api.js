// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Open Observe API', {
    refresh: function(frm) {
        // Add a button to test connection
        frm.add_custom_button(__('Test Connection'), function() {
            frappe.call({
                method: 'tweaks.tweaks.doctype.open_observe_api.open_observe_api.test_connection',
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Success'),
                            indicator: 'green',
                            message: __(r.message.message)
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: __(r.message ? r.message.error : 'Connection test failed')
                        });
                    }
                }
            });
        });
    }
});
