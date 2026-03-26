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


@frappe.whitelist()
def bake_customizations(filters=None):
    """Bake filtered customizations directly onto each unique DocType and save."""
    frappe.only_for("System Manager")

    if isinstance(filters, str):
        filters = json.loads(filters)

    from tweaks.tweaks.report.form_customizations.form_customizations import get_data

    rows = get_data(filters or {})

    dt_rows: dict = {}
    for row in rows:
        dt = row.get("dt")
        if dt:
            dt_rows.setdefault(dt, []).append(row)

    baked = 0
    errors = {}

    for dt in sorted(dt_rows):
        try:
            doc = frappe.get_doc("DocType", dt)
            _apply_rows_to_doc(doc, dt_rows[dt])
            doc.save()
            baked += 1
        except Exception as e:
            errors[dt] = str(e)
            frappe.logger().warning(
                "bake_customizations: failed to save DocType %s: %s", dt, e
            )

    return {"baked": baked, "failed": len(errors), "errors": errors}


_CF_DOCFIELD_FIELDS = frozenset(
    {
        "fieldname",
        "label",
        "fieldtype",
        "options",
        "default",
        "description",
        "depends_on",
        "mandatory_depends_on",
        "read_only_depends_on",
        "reqd",
        "hidden",
        "bold",
        "in_list_view",
        "in_standard_filter",
        "read_only",
        "allow_on_submit",
        "search_index",
        "no_copy",
        "print_hide",
        "print_hide_if_no_value",
        "fetch_from",
        "fetch_if_empty",
        "permlevel",
        "precision",
        "length",
        "columns",
        "translatable",
        "unique",
        "insert_after",
    }
)


def _apply_rows_to_doc(doc, rows):
    """Apply Custom Field and Property Setter rows onto a DocType document in memory."""
    for row in rows:
        name = row.get("customization_name")
        if not name:
            continue

        if row["customization_type"] == "Custom Field":
            cf = frappe.get_doc("Custom Field", name)
            cf_dict = {
                k: v for k, v in cf.as_dict().items() if k in _CF_DOCFIELD_FIELDS
            }
            insert_after = cf_dict.get("insert_after")
            position = -1
            if insert_after:
                idx = next(
                    (
                        i
                        for i, f in enumerate(doc.fields)
                        if f.fieldname == insert_after
                    ),
                    None,
                )
                if idx is not None:
                    position = idx + 1
            doc.append("fields", cf_dict, position)

        elif row["customization_type"] == "Property Setter":
            prop = row.get("property")
            value = row.get("value")
            if not prop:
                continue
            # Frappe rejects default_print_format on standard DocTypes during save
            if prop == "default_print_format":
                continue
            if row.get("doctype_or_field") == "DocType":
                setattr(doc, prop, value)
            else:
                fieldname = row.get("fieldname")
                for field in doc.fields:
                    if field.fieldname == fieldname:
                        setattr(field, prop, value)
                        break


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
