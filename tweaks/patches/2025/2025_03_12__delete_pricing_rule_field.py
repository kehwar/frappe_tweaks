import frappe


def execute():

    cf = frappe.db.get_value(
        "Custom Field", {"dt": "Pricing Rule", "fieldname": "script"}
    )
    if cf:
        frappe.delete_doc("Custom Field", cf)
