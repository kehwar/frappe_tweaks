from frappe.utils.caching import site_cache

from tweaks.utils.changelog import frappe_version


@site_cache
def allow_value():
    if frappe_version() <= 15:
        return None  # Falthrough and be evaluated by other hooks
    return True
