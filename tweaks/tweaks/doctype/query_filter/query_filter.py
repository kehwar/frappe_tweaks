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
        if hasattr(super(), "clear_cache"):
            super().clear_cache()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def on_trash(self):
        """Clear AC rule cache when query filter is deleted"""
        if hasattr(super(), "on_trash"):
            super().on_trash()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    @frappe.whitelist()
    def get_sql(self, user=None) -> str:
        return get_sql(self, user=user)


def get_sql(query_filter: str | QueryFilter | dict, user=None):

    if isinstance(query_filter, str):
        query_filter = frappe.get_doc("Query Filter", query_filter).as_dict()
    elif isinstance(query_filter, QueryFilter):
        query_filter = query_filter.as_dict()

    filters = query_filter.get("filters", "")
    filters_type = query_filter.get("filters_type", "JSON")
    reference_doctype = query_filter.get("reference_doctype", "")
    reference_docname = query_filter.get("reference_docname", "")

    # Default to session user if not provided
    if user is None:
        user = frappe.session.user

    if not filters:
        return "1=1"

    if filters_type == "SQL":
        return filters

    if reference_doctype and reference_docname:
        return (
            f"`tab{reference_doctype}`.`name` = {frappe.db.escape(reference_docname)}"
        )

    # Helper function to build SQL from filters
    def build_sql_from_filters(filter_data):
        if not reference_doctype:
            frappe.throw("Reference Doctype is required when using filters")
        sql = frappe.get_all(
            reference_doctype, filters=filter_data, order_by="", distinct=1, run=0
        )
        flat_sql = sql.strip().replace("\n", " ").replace("\r", " ")
        return f"`tab{reference_doctype}`.`name` IN ({flat_sql})"

    if filters_type == "Python":
        loc = {
            "resource": query_filter,
            "conditions": "",
            "filters": None,
            "user": user,
        }
        safe_exec(
            filters,
            None,
            loc,
            script_filename=f"Resource Filter {query_filter.get('name')}",
        )
        # Check conditions first
        if loc["conditions"]:
            return loc["conditions"]
        # Fall back to filters dict/array
        if loc.get("filters") is not None:
            return build_sql_from_filters(loc["filters"])
        return "1=0"

    if filters_type == "JSON":
        return build_sql_from_filters(filters)

    return "1=1"
