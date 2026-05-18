import frappe


@frappe.whitelist()
def switch_language(language):
	frappe.db.set_value("User", frappe.session.user, "language", language)
	frappe.clear_cache(user=frappe.session.user)
