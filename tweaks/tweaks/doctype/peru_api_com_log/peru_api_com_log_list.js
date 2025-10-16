// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

/**
 * List view settings for PERU API COM Log doctype.
 * Configures custom buttons and menu items for log management functionality.
 */
frappe.listview_settings['PERU API COM Log'] = {
    /**
     * Onload event handler for PERU API COM Log list view.
     * Orchestrates the setup of navigation and administrative features.
     * @param {Object} listview - The list view object
     */
    onload: function(listview) {
        this.setup_navigation_buttons(listview);
        this.setup_administrative_menu_items(listview);
    },

    /**
     * Sets up navigation buttons for quick access to related functionality.
     * @param {Object} listview - The list view object
     */
    setup_navigation_buttons: function(listview) {
        listview.page.add_button(__('Console'), function() {
            frappe.set_route('Form', 'PERU API COM Console');
        });
    },

    /**
     * Sets up administrative menu items for configuration and maintenance.
     * @param {Object} listview - The list view object
     */
    setup_administrative_menu_items: function(listview) {
        // Add Settings menu item for configuration
        listview.page.add_menu_item(__('Settings'), function() {
            frappe.set_route("List", "PERU API COM");
        });
        
        // Add Clear Logs menu item with confirmation
        listview.page.add_menu_item(__("Clear API Logs"), function () {
            frappe.listview_settings['PERU API COM Log'].clear_api_logs(listview);
        });
    },

    /**
     * Clears all API logs with proper callback handling.
     * @param {Object} listview - The list view object
     */
    clear_api_logs: function(listview) {
        frappe.call({
            method: "tweaks.tweaks.doctype.peru_api_com_log.peru_api_com_log.clear_api_logs",
            callback: function () {
                listview.refresh();
            },
        });
    },
    hide_name_column: true,
};