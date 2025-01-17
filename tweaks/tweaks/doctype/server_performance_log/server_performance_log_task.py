import frappe
from frappe import get_site_path, new_doc
from frappe.utils import now
from psutil import cpu_percent, disk_usage, virtual_memory


def execute():

    if (
        frappe.flags.in_patch
        or frappe.flags.in_install
        or frappe.flags.in_migrate
        or frappe.flags.in_import
        or frappe.flags.in_setup_wizard
    ):
        return

    perf_log = new_doc("Server Performance Log")
    perf_log.cpu_utilisation = cpu_percent()
    perf_log.ram_utilisation = virtual_memory().percent
    perf_log.disk_utilisation = disk_usage(get_site_path()).percent
    perf_log.log_date = now()
    perf_log.save()
