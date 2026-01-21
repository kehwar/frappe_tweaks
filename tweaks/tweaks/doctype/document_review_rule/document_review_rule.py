# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists


class DocumentReviewRule(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF
        from tweaks.tweaks.doctype.document_review_user.document_review_user import DocumentReviewUser

        assign_condition: DF.Code | None
        disabled: DF.Check
        mandatory: DF.Check
        reference_doctype: DF.Link
        script: DF.Code
        submit_condition: DF.Code | None
        title: DF.Data
        unassign_condition: DF.Code | None
        users: DF.Table[DocumentReviewUser]
        validate_condition: DF.Code | None
    # end: auto-generated types

    def on_update(self):
        """Invalidate cache when rule is updated."""
        self.clear_cache()

    def on_trash(self):
        """Invalidate cache when rule is deleted."""
        self.clear_cache()

    def clear_cache(self):
        """Clear the cached rules for this doctype."""
        cache_key = f"document_review_rules:{self.reference_doctype}"
        frappe.cache.delete_value(cache_key)

    def autoname(self):
        """Set name from title."""
        self.name = append_number_if_name_exists("Document Review Rule", self.title)
