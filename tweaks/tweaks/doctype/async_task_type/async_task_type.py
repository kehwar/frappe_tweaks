# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AsyncTaskType(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        is_standard: DF.Check
        concurrency_limit: DF.Int
        method: DF.Data
        priority: DF.Int
    # end: auto-generated types

    def validate(self):
        if (
            self.is_standard
            and not frappe.conf.developer_mode
            and not (frappe.flags.in_migrate or frappe.flags.in_patch)
        ):
            if self.is_new():
                frappe.throw(
                    _("You are not allowed to create standard Async Task Type")
                )
            elif self.has_value_changed("method"):
                frappe.throw(
                    _("Method cannot be changed for a standard Async Task Type")
                )

    def on_trash(self):
        if (
            self.is_standard
            and not frappe.conf.developer_mode
            and not (frappe.flags.in_migrate or frappe.flags.in_patch)
        ):
            frappe.throw(_("You are not allowed to delete standard Async Task Type"))
