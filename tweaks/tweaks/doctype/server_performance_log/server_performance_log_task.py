from frappe import get_site_path, new_doc
from psutil import cpu_percent, disk_usage, virtual_memory


def execute():
    perf_log = new_doc("Server Performance Log")
    perf_log.cpu_utilisation = cpu_percent()
    perf_log.ram_utilisation = virtual_memory().percent
    perf_log.disk_utilisation = disk_usage(get_site_path()).percent
    perf_log.save()
