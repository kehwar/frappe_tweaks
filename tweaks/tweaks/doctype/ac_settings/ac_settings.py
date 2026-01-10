# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ACSettings(Document):
    pass


@frappe.whitelist()
def clear_ac_cache():
    """Clear all AC Rule caches"""
    frappe.only_for("System Manager")
    
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache
    
    clear_ac_rule_cache()
    
    frappe.msgprint("AC Rule cache cleared successfully", alert=True)
