import frappe
from frappe.desk.form import utils as form_utils
from frappe.model.base_document import get_controller
from frappe.model.utils import is_virtual_doctype


@frappe.whitelist()
def get_next(
    doctype, value, prev, filters=None, sort_order="desc", sort_field="modified"
):

    if is_virtual_doctype(doctype):
        controller = get_controller(doctype)
        if hasattr(controller, "get_next"):
            return controller.get_next(
                doctype,
                value,
                prev,
                filters=filters,
                sort_order=sort_order,
                sort_field=sort_field,
            )

    return form_utils.get_next(doctype, value, prev, filters, sort_order, sort_field)
