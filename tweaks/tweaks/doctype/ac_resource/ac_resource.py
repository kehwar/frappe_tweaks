# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.model.document import Document


class ACResource(Document):

    def before_validate(self):

        if self.type != "DocType":
            self.document_type = None
        if self.type != "Report":
            self.report = None
        self.fieldname = self.fieldname.strip() if self.fieldname else ""
        if self.managed_actions != "Select":
            self.actions = []

    def validate(self):

        if not self.type:
            frappe.throw(_("Type is required"))
        if self.type == "DocType" and not self.document_type:
            frappe.throw(_("Document Type is required"))
        if self.type == "Report" and not self.report:
            frappe.throw(_("Report is required"))
        if self.managed_actions == "Select" and not self.actions:
            frappe.throw(_("At least one Action is required"))

        if (
            self.is_standard
            and not frappe.conf.developer_mode
            and not (frappe.flags.in_migrate or frappe.flags.in_patch)
        ):
            if self.is_new():
                frappe.throw(_("You are not allowed to create standard AC Resource"))
            elif (
                self.has_value_changed("type")
                or self.has_value_changed("document_type")
                or self.has_value_changed("report")
                or self.has_value_changed("fieldname")
            ):
                frappe.throw(
                    _(
                        "Type, Document Type, or Report cannot be changed for a standard AC Resource"
                    )
                )

    def clear_cache(self):
        """Clear AC rule cache"""
        super().clear_cache()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def on_trash(self):
        """Clear AC rule cache when resource is deleted"""
        super().on_trash()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        if (
            self.is_standard
            and not frappe.conf.developer_mode
            and not (frappe.flags.in_migrate or frappe.flags.in_patch)
        ):
            frappe.throw(_("You are not allowed to delete standard AC Resource"))

        clear_ac_rule_cache()
