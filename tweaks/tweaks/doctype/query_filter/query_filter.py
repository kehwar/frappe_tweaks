# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec


class QueryFilter(Document):

    def before_validate(self):

        if self.reference_doctype and self.reference_docname:
            self.filters = frappe.as_json(["name", "=", self.reference_docname])
            self.filters_type = "JSON"

    def validate(self):

        if self.filters_type == "JSON" and not self.reference_doctype:
            frappe.throw("Reference Doctype is required for JSON type filters")

    def clear_cache(self):
        """Clear AC rule cache"""
        super().clear_cache()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def on_trash(self):
        """Clear AC rule cache when query filter is deleted"""
        super().on_trash()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    @frappe.whitelist()
    def get_sql(self) -> str:
        return get_sql(self)


@frappe.request_cache
def get_sql(query_filter: str | QueryFilter | dict):

    if isinstance(query_filter, str):
        query_filter = frappe.get_doc("Resource Filter", query_filter).as_dict()
    elif isinstance(query_filter, QueryFilter):
        query_filter = query_filter.as_dict()

    filters = query_filter.get("filters", "")
    filters_type = query_filter.get("filters_type", "JSON")
    reference_doctype = query_filter.get("reference_doctype", "")
    reference_docname = query_filter.get("reference_docname", "")

    if not filters:
        return "1=1"

    if filters_type == "SQL":
        return filters

    if filters_type == "Python":
        loc = {"resource": query_filter, "conditions": ""}
        safe_exec(
            filters,
            None,
            loc,
            script_filename=f"Resource Filter {query_filter.get('name')}",
        )
        if loc["conditions"]:
            return loc["conditions"]
        return "1=0"

    if reference_doctype and reference_docname:
        return (
            f"`tab{reference_doctype}`.`name` = {frappe.db.escape(reference_docname)}"
        )

    if reference_doctype and filters_type == "JSON":
        sql = frappe.get_all(
            reference_doctype, filters=filters, order_by="", distinct=1, run=0
        )
        flat_sql = sql.strip().replace("\n", " ").replace("\r", " ")
        return f"`tab{reference_doctype}`.`name` IN ({flat_sql})"

    return "1=1"
