# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BusinessLogicLink(Document):
    pass


def on_doctype_update():
    frappe.db.add_index("Business Logic Link", ["link_doctype", "link_name"])
    frappe.db.add_index("Business Logic Link", ["action", "link_doctype", "link_name"])
