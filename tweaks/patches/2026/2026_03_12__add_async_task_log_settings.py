# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import frappe


def execute():
    """Add Log Settings for Async Task Log auto-cleanup"""

    log_settings = frappe.get_doc("Log Settings")
    log_settings.register_doctype("Async Task Log", 30)
    log_settings.save()
