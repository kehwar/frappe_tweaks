# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ACAction(Document):

    def validate(self):

        if self.disabled and not frappe.db.exists(
            "AC Action", [["disabled", "=", 0], ["name", "!=", self.name]]
        ):
            frappe.throw(_("At least one action must be enabled."))


def insert_standard_actions():

    actions = [
        "Read",
        "Write",
        "Create",
        "Delete",
        "Submit",
        "Cancel",
        "Select",
        "Amend",
        "Print",
        "Email",
        "Report",
        "Import",
        "Export",
        "Share",
    ]

    for action in actions:

        if frappe.db.exists("AC Action", action):

            continue

        frappe.get_doc(
            {
                "doctype": "AC Action",
                "action": action,
                "is_standard": 1,
            }
        ).insert(ignore_permissions=True)
