// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

/**
 * List view settings for PERU API COM Log doctype.
 * Configures custom buttons and menu items for log management functionality.
 */
frappe.listview_settings['PERU API COM Log'] = {
    /**
     * Onload event handler for PERU API COM Log list view.
     * Sets up navigation buttons and administrative actions.
     * @param {Object} listview - The list view object
     */
    onload: function(listview) {
        // Add Console button for quick access to testing interface
        listview.page.add_button(__('Console'), function() {
            frappe.set_route('Form', 'PERU API COM Console');
        });
        
        // Add Settings menu item for configuration
        listview.page.add_menu_item(__('Settings'), function() {
            frappe.set_route("List", "PERU API COM");
        });
        
        // Add Clear Logs menu item with confirmation
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