import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from sqlalchemy import table


def execute():

    log_settings = frappe.get_single("Log Settings")
    log_settings.logs_to_clear = [
        log
        for log in log_settings.logs_to_clear
        if log.ref_doctype != "Server Performance Log"
    ]
    log_settings.save()

    if frappe.db.has_table("tabServer Performance Log"):
        frappe.db.sql("DROP TABLE `tabServer Performance Log`")
        frappe.db.commit()
