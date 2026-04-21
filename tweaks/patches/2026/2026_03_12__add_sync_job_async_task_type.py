# Copyright (c) 2026, and contributors
# See license.txt

import frappe


def execute():
    """Add Async Task Type for execute_sync_job with concurrency_limit=1"""

    frappe.get_doc(
        {
            "doctype": "Async Task Type",
            "method": "tweaks.tweaks.doctype.sync_job.sync_job.execute_sync_job",
            "concurrency_limit": 1,
            "is_standard": 1,
        }
    ).insert(ignore_if_duplicate=True)
