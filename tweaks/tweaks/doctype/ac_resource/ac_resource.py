# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.utils.nestedset import NestedSet
from frappe.utils.safe_exec import safe_exec


class ACResource(NestedSet):

    def before_validate(self):

        if self.parent_ac_resource:
            self.type = "Child"
            self.managed_actions = "Inherit from parent"
        if self.type != "DocType":
            self.document_type = None
        if self.type != "Report":
            self.report = None
        if self.type != "Custom":
            self.custom = ""
        else:
            self.custom = self.custom.strip()
        self.fieldname = self.fieldname.strip() if self.fieldname else ""
        if self.managed_actions != "Select":
            self.actions = []
        if self.type in ("DocType", "Report", "Custom"):
            self.parent_ac_resource = None
            self.is_group = 1
            self.condition_script = None

    def validate(self):

        if not self.type:
            frappe.throw(_("Type is required"))
        if self.type == "DocType" and not self.document_type:
            frappe.throw(_("Document Type is required"))
        if self.type == "Report" and not self.report:
            frappe.throw(_("Report is required"))
        if self.type == "Custom" and not self.custom:
            frappe.throw(_("Custom is required"))
        if self.managed_actions == "Select" and not self.actions:
            frappe.throw(_("At least one Action is required"))
        if self.type == "Child" and not self.parent_ac_resource:
            frappe.throw(_("Parent AC Resource is required for Child type"))
        if (
            self.managed_actions == "Inherit from parent"
            and not self.parent_ac_resource
        ):
            frappe.throw(_("Parent AC Resource is required for Inherit from parent"))
        if not self.condition_script:
            self.script_type = None
        else:
            self.script_type = self.script_type or "Python"

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
                or self.has_value_changed("custom")
                or self.has_value_changed("fieldname")
            ):
                frappe.throw(
                    _(
                        "Type, Document Type, Report or API Name cannot be changed for a standard AC Resource"
                    )
                )

    def on_trash(self):
        if (
            self.is_standard
            and not frappe.conf.developer_mode
            and not (frappe.flags.in_migrate or frappe.flags.in_patch)
        ):
            frappe.throw(_("You are not allowed to delete standard AC Resource"))


@frappe.request_cache
def run_script(script, resource=""):
    if not script:
        return ""
    loc = {"resource": resource, "conditions": None}
    safe_exec(script, None, loc, script_filename=f"AC Resource {resource}")
    if loc["conditions"]:
        return loc["conditions"]
    return ""
