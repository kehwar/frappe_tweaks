// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.listview_settings['PERU API COM Log'] = {
    onload: function(listview) {
        listview.page.add_button(__('Console'), function() {
            frappe.set_route('Form', 'PERU API COM Console');
        });
        listview.page.add_menu_item(__('Settings'), function() {
            frappe.set_route("List", "PERU API COM");
        });
        listview.page.add_menu_item(__("Clear API Logs"), function () {
            frappe.call({
                method: "tweaks.tweaks.doctype.peru_api_com_log.peru_api_com_log.clear_api_logs",
                callback: function () {
                    listview.refresh();
                },
            });
        });
    }
};