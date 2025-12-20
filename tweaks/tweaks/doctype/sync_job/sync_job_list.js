// Copyright (c) 2025, and contributors
// For license information, please see license.txt

/**
 * List view settings for Sync Job doctype.
 * Configures custom buttons and menu items for log management functionality.
 */
frappe.listview_settings['Sync Job'] = {
    /**
     * Onload event handler for Sync Job list view.
     * Sets up administrative features and menu items.
     * @param {Object} listview - The list view object
     */
    onload: function(listview) {
        this.setup_administrative_menu_items(listview);
    },

    /**
     * Sets up administrative menu items for maintenance.
     * @param {Object} listview - The list view object
     */
    setup_administrative_menu_items: function(listview) {
        // Add Clear All Logs menu item with confirmation
        listview.page.add_menu_item(__("Clear All Logs"), function () {
            frappe.listview_settings['Sync Job'].clear_all_logs(listview);
        });
    },

    /**
     * Clears all sync job logs with confirmation dialog.
     * @param {Object} listview - The list view object
     */
    clear_all_logs: function(listview) {
        frappe.confirm(
            __('Are you sure you want to clear all sync job logs? This action cannot be undone.'),
            function() {
                frappe.call({
                    method: "tweaks.tweaks.doctype.sync_job.sync_job.clear_all_logs",
                    callback: function () {
                        frappe.show_alert({
                            message: __('All sync job logs have been cleared'),
                            indicator: 'green'
                        });
                        listview.refresh();
                    },
                });
            }
        );
    },
};
