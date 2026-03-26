# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _

from tweaks.tweaks.doctype.async_task_log.async_task_log import enqueue_async_task


@frappe.whitelist()
def enqueue_delete_customizations(filters=None):
    """Enqueue a background task to delete Custom Fields and Property Setters matching filters."""
    frappe.only_for("System Manager")

    if isinstance(filters, str):
        filters = json.loads(filters)

    task = enqueue_async_task(
        method=delete_customizations,
        job_name=_("Delete Form Customizations"),
        queue="long",
        filters=filters or {},
    )

    return task.name


def delete_customizations(filters=None):
    """
    Delete Custom Fields and Property Setters matching the given filters.

    Delegates to the report's get_data() to collect matching rows, then
    permanently deletes each Custom Field or Property Setter found.
    """
    from tweaks.tweaks.report.form_customizations.form_customizations import get_data

    rows = get_data(filters or {})

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
        "delete_customizations: deleted %d Custom Field(s) and %d Property Setter(s)",
        deleted_cf,
        deleted_ps,
    )
