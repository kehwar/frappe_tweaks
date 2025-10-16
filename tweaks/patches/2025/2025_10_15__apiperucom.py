import frappe
from frappe.model.base_document import get_controller


def execute():

    log_settings = frappe.get_doc("Log Settings")
    log_settings.register_doctype("PERU API COM Log", 30)
    log_settings.save()