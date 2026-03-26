# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from tweaks.tweaks.doctype.async_task_log.async_task_log import enqueue_async_task


@frappe.whitelist()
def enqueue_delete_stale_customizations():
    """Enqueue a background task to delete all stale Custom Fields and Property Setters."""
    frappe.only_for("System Manager")

    task = enqueue_async_task(
        method=delete_stale_customizations,
        job_name=_("Delete Stale Form Customizations"),
        queue="long",
    )

    return task.name


def delete_stale_customizations():
    """
    Delete all stale Custom Fields and Property Setters.

    A customization is "Stale" when the native DocType already defines the
    same field / property with an identical value, making the customization
    redundant.  This function re-uses the report's get_data() logic with a
    Stale status filter to collect the candidates, then deletes them.
    """
    from tweaks.tweaks.report.form_customizations.form_customizations import get_data

    rows = get_data({"status": "Stale", "show_system_generated": 1})

    deleted_cf = 0
    deleted_ps = 0

    for row in rows:
        name = row.get("customization_name")
        if not name:
            continue

        if row.get("customization_type") == "Custom Field":
            frappe.delete_doc("Custom Field", name, ignore_missing=True, force=True)
            deleted_cf += 1
        elif row.get("customization_type") == "Property Setter":
            frappe.delete_doc("Property Setter", name, ignore_missing=True, force=True)
            deleted_ps += 1

    frappe.db.commit()

    frappe.logger().info(
        "delete_stale_customizations: deleted %d Custom Field(s) and %d Property Setter(s)",
        deleted_cf,
        deleted_ps,
    )
