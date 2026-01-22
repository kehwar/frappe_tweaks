# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DocumentReview(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        mandatory: DF.Check
        message: DF.TextEditor | None
        naming_series: DF.Literal["DR-.YYYY.-"]
        reference_doctype: DF.Data
        reference_name: DF.DynamicLink
        reference_title: DF.Data | None
        review_data: DF.JSON | None
        review_rule: DF.Link
        title: DF.Data | None
    # end: auto-generated types

    def before_save(self):
        """Populate reference title from linked document."""
        if self.reference_doctype and self.reference_name:
            try:
                meta = frappe.get_meta(self.reference_doctype)
                title_field = meta.get_title_field()

                if title_field:
                    self.reference_title = frappe.get_value(
                        self.reference_doctype, self.reference_name, title_field
                    )
                else:
                    self.reference_title = self.reference_name
            except Exception:
                self.reference_title = self.reference_name

    def on_change(self):
        """Notify linked document about the change."""

        reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
        reference_doc.notify_update()

    def on_submit(self):
        """Trigger referenced document on_change to re-evaluate conditions."""
        # Get the referenced document
        try:
            reference_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
            # Trigger on_change to re-evaluate all conditions including assignment/unassignment
            reference_doc.notify_update()
        except Exception as e:
            frappe.log_error(
                title=f"Failed to notify reference document {self.reference_doctype} {self.reference_name}",
                message=str(e),
            )
