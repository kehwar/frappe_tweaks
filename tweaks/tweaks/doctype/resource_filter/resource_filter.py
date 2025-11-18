# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec


class ResourceFilter(Document):

    def before_validate(self):

        if self.reference_doctype and self.reference_docname:
            self.filters = frappe.as_json(["name", "=", self.reference_docname])
            self.filters_type = "JSON"

    def validate(self):

        if self.filters_type == "JSON" and not self.reference_doctype:
            frappe.throw("Reference Doctype is required for JSON type filters")

    @frappe.whitelist()
    def get_sql(self) -> str:
        return get_sql(self)


@frappe.request_cache
def get_sql(resource_filter: str | ResourceFilter | dict):

    if isinstance(resource_filter, str):
        resource_filter = frappe.get_doc("Resource Filter", resource_filter).as_dict()
    elif isinstance(resource_filter, ResourceFilter):
        resource_filter = resource_filter.as_dict()

    filters = resource_filter.get("filters", "")
    filters_type = resource_filter.get("filters_type", "JSON")
    reference_doctype = resource_filter.get("reference_doctype", "")
    reference_docname = resource_filter.get("reference_docname", "")

    if not filters:
        return ""

    if filters_type == "SQL":
        return filters

    if filters_type == "Python":
        loc = {"resource": resource_filter, "conditions": ""}
        safe_exec(
            filters,
            None,
            loc,
            script_filename=f"Resource Filter {resource_filter.get('name')}",
        )
        if loc["filters_sql"]:
            return loc["filters_sql"]
        return ""

    if reference_doctype and reference_docname:
        return (
            f"`tab{reference_doctype}`.`name` = {frappe.db.escape(reference_docname)}"
        )

    if filters_type == "JSON" and reference_doctype:
        sql = frappe.get_all(
            reference_doctype, filters=filters, order_by="", distinct=1, run=0
        )
        flat_sql = sql.strip().replace("\n", " ").replace("\r", " ")
        return f"`tab{reference_doctype}`.`name` IN ({flat_sql})"

    return ""
