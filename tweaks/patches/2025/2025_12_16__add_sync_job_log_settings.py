# Copyright (c) 2025, and contributors
# For license information, please see license.txt

import frappe


def execute():
    """Add Log Settings for Sync Job auto-cleanup"""

    log_settings = frappe.get_doc("Log Settings")
    log_settings.register_doctype("Sync Job", 30)
    log_settings.save()
