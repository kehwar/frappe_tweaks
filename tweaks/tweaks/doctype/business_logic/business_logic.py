# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BusinessLogic(Document):

    def autoname(self):
        naming_series = ["BL"]
        category_series = frappe.db.get_value(
            "Business Logic Category", self.category, "naming_series"
        )
        naming_series.append(category_series) if category_series else None
        naming_series.append(str(frappe.utils.getdate().year))
        naming_series.append("")

        self.naming_series = "-".join(naming_series)

    def before_validate(self):
        self.set_link_title()

    def set_link_title(self):
        if not self.links:
            return
        for link in self.links:
            linked_doc = frappe.get_doc(link.link_doctype, link.link_name)
            doc_title = linked_doc.get_title()
            if link.link_title != doc_title:
                link.link_title = doc_title or link.link_name
