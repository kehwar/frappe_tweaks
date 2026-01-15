# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.model.document import Document


class ACAction(Document):

    def validate(self):
        self.validate_unique_scrubbed_name()

        if self.disabled and not frappe.db.exists(
            "AC Action", [["disabled", "=", 0], ["name", "!=", self.name]]
        ):
            frappe.throw(_("At least one action must be enabled."))

    def validate_unique_scrubbed_name(self):
        """Ensure no other action exists with the same scrubbed name"""
        scrubbed_name = scrub(self.action)

        # Check if any other action has the same scrubbed name
        existing = frappe.db.get_all(
            "AC Action",
            filters={"name": ["!=", self.name]},
            fields=["name", "action"],
            pluck="action",
        )

        for existing_action in existing:
            if scrub(existing_action) == scrubbed_name:
                frappe.throw(
                    _(
                        "An action with the scrubbed name '{0}' already exists: {1}"
                    ).format(scrubbed_name, existing_action)
                )

    def clear_cache(self):
        """Clear AC rule cache"""
        if hasattr(super(), "clear_cache"):
            super().clear_cache()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def on_trash(self):
        """Clear AC rule cache when action is deleted"""
        if hasattr(super(), "on_trash"):
            super().on_trash()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()


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
