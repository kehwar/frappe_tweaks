import frappe
from frappe.utils.caching import site_cache


@site_cache
def frappe_version():

    frappe_version = frappe.__version__.split(".")[0]
    return int(frappe_version)
