# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils.safe_exec import safe_exec


class ACPrincipal(NestedSet):

    def before_validate(self):

        if self.type != "User":
            self.user = None
        if self.type != "Role":
            self.role = None
        if self.type != "User Group":
            self.user_group = None
        if self.type != "User Script":
            self.user_script = None
            self.script_type = None
        else:
            self.script_type = self.script_type or "Python"

    def validate(self):

        if self.type == "User" and not self.user:
            frappe.throw(_("User is required"))
        if self.type == "Role" and not self.role:
            frappe.throw(_("Role is required"))
        if self.type == "User Group" and not self.user_group:
            frappe.throw(_("User Group is required"))
        if self.type == "User Script" and not self.user_script:
            frappe.throw(_("User Script is required"))


@frappe.request_cache
def run_script(script, principal=""):
    if not script:
        return ""
    loc = {"principal": principal, "conditions": None}
    safe_exec(script, None, loc, script_filename=f"AC Principal {principal}")
    print(loc)
    if loc["conditions"]:
        return loc["conditions"]
    return ""
