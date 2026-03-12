# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Client-facing whitelisted APIs for the Async Task Log list view.
"""

import frappe
from frappe import _


@frappe.whitelist()
def bulk_action(
    docnames: list[str] | str,
    action: str,
    data: dict | str | None = None,
    task_id: str | None = None,
) -> list[str]:
    """
    Execute *action* on a list of Async Task Log documents.

    Mirrors :func:`frappe.desk.doctype.bulk_update.bulk_update.submit_cancel_or_update_docs`:
    runs inline for small batches, enqueues for larger ones.

    :param docnames: List of Async Task Log names (or JSON-encoded list).
    :param action: One of ``"enqueue"``, ``"pause"``, ``"resume"``, ``"cancel"``, ``"retry"``.
    :param data: Optional JSON dict of extra keyword arguments (e.g. ``{"message": "…"}`` for cancel).
    :param task_id: Optional Frappe task ID for progress publishing.
    :returns: List of docnames that could not be processed.
    """
    if isinstance(docnames, str):
        docnames = frappe.parse_json(docnames)

    if len(docnames) < 20:
        return _bulk_action(docnames, action, data, task_id)

    if len(docnames) <= 500:
        frappe.msgprint(_("Bulk operation is enqueued in background."), alert=True)
        frappe.enqueue(
            _bulk_action,
            docnames=docnames,
            action=action,
            data=data,
            task_id=task_id,
            queue="short",
            timeout=1000,
        )
        return []

    frappe.throw(
        _("Bulk operations only support up to 500 documents."),
        title=_("Too Many Documents"),
    )


def _bulk_action(
    docnames: list[str],
    action: str,
    data: dict | str | None = None,
    task_id: str | None = None,
) -> list[str]:
    if isinstance(data, str):
        data = frappe.parse_json(data)
    data = data or {}

    failed = []
    num_documents = len(docnames)

    for idx, docname in enumerate(docnames, 1):
        try:
            doc = frappe.get_doc("Async Task Log", docname)
            if action == "enqueue":
                doc.enqueue_execution()
            elif action == "pause":
                if doc.status == "Pending":
                    doc.toggle_pause()
                else:
                    failed.append(docname)
                    continue
            elif action == "resume":
                if doc.status == "Paused":
                    doc.toggle_pause()
                else:
                    failed.append(docname)
                    continue
            elif action == "cancel":
                doc.cancel(**data)
            elif action == "retry":
                doc.retry()
            else:
                frappe.throw(_("Unknown action: {0}").format(action))

            frappe.db.commit()
            frappe.publish_progress(
                percent=idx / num_documents * 100,
                title=_("Processing {0}").format(action),
                description=docname,
                task_id=task_id,
            )
        except Exception:
            failed.append(docname)
            frappe.db.rollback()

    return failed
