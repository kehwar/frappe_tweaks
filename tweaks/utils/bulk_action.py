import frappe
from frappe import _, is_whitelisted
from frappe.utils.scheduler import is_scheduler_inactive


@frappe.whitelist()
def run_doc_method(doctype, docnames, method, kwargs=None, task_id=None):
    """Run an arbitrary method on a list of documents.

    Args:
            doctype: The DocType name.
            docnames: List (or JSON string) of document names.
            method: The method name to call on each document.
            kwargs: Optional dict (or JSON string) of keyword arguments to pass to the method.
            task_id: Optional task ID for progress publishing.
    """
    if isinstance(docnames, str):
        docnames = frappe.parse_json(docnames)

    if len(docnames) < 20:
        return _run_doc_method(doctype, docnames, method, kwargs, task_id)
    elif len(docnames) <= 500:
        frappe.msgprint(_("Bulk operation is enqueued in background."), alert=True)
        frappe.enqueue(
            _run_doc_method,
            doctype=doctype,
            docnames=docnames,
            method=method,
            kwargs=kwargs,
            task_id=task_id,
            queue="short",
            timeout=1000,
        )
    else:
        frappe.throw(
            _("Bulk operations only support up to 500 documents."),
            title=_("Too Many Documents"),
        )


def _run_doc_method(doctype, docnames, method, kwargs=None, task_id=None):
    if kwargs:
        kwargs = frappe.parse_json(kwargs)
    else:
        kwargs = {}

    failed = []
    num_documents = len(docnames)

    for idx, docname in enumerate(docnames, 1):
        doc = frappe.get_doc(doctype, docname)
        try:
            if not hasattr(doc, method):
                frappe.throw(_("{0} does not have method {1}").format(doctype, method))

            method_obj = getattr(doc, method)
            fn = getattr(method_obj, "__func__", method_obj)
            is_whitelisted(fn)

            method_obj(**kwargs)
            frappe.db.commit()
            frappe.publish_progress(
                percent=idx / num_documents * 100,
                title=_("Running {0} on {1}").format(method, doctype),
                description=docname,
                task_id=task_id,
            )
        except Exception:
            failed.append(docname)
            frappe.db.rollback()

    return failed
