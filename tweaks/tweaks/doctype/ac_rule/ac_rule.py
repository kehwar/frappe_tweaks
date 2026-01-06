# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.utils.nestedset import NestedSet, get_ancestors_of, get_descendants_of


class ACRule(Document):

    def validate(self):

        if len([p for p in self.principals if not p.exception]) == 0:
            frappe.throw(_("At least one principal filter must not be an exception."))
        self.validate_resource_filters()

    def clear_cache(self):
        """Clear AC rule cache"""
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def on_trash(self):
        """Clear AC rule cache when rule is deleted"""
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def validate_resource_filters(self):

        resource = frappe.get_doc("AC Resource", self.resource)

        for filter in self.resources:

            query_filter = frappe.get_doc("Query Filter", filter.filter)

            if (
                resource.document_type
                and resource.document_type != query_filter.reference_doctype
            ):
                frappe.throw(
                    _(
                        "Resource Filter '{0}' is not valid for resource '{1}' because the resource's document type is '{2}' but the filter's reference doctype is '{3}'."
                    ).format(
                        query_filter.get_title(),
                        resource.get_title(),
                        resource.document_type,
                        query_filter.reference_doctype,
                    )
                )

            if resource.report and resource.report != query_filter.reference_report:
                frappe.throw(
                    _(
                        "Resource Filter '{0}' is not valid for resource '{1}' because the resource's report is '{2}' but the filter's reference report is '{3}'."
                    ).format(
                        query_filter.get_title(),
                        resource.get_title(),
                        resource.report,
                        query_filter.reference_report,
                    )
                )

    def resolve_principals(self, debug=False):

        filters = []

        for row in self.principals:

            query_filter = frappe.get_doc("Query Filter", row.filter)

            r = frappe._dict(
                {
                    "name": query_filter.name,
                    "doctype": query_filter.reference_doctype,
                }
            )

            if debug:
                r["title"] = query_filter.get_title()
                if query_filter.reference_doctype:
                    r["reference_doctype"] = query_filter.reference_doctype
                if query_filter.reference_report:
                    r["reference_report"] = query_filter.reference_report
                if query_filter.reference_docname:
                    r["reference_docname"] = query_filter.reference_docname
                if query_filter.filters_type:
                    r["filters_type"] = query_filter.filters_type
                if query_filter.filters:
                    r["filters"] = query_filter.filters

            if row.exception:
                r["exception"] = 1

            filters.append(r)

        return filters

    def resolve_principals_deprecated(self, debug=False):

        allowed = set()
        denied = set()

        for p in self.principals:

            principals = [p.principal]
            if p.recursive:
                principals += get_descendants_of(
                    "AC Principal", p.principal, ignore_permissions=1
                )

            if p.exception:
                denied.update(principals)
            else:
                allowed.update(principals)

        allowed = allowed - denied

        if len(allowed) == 0:
            return []

        principals = []

        for principal in allowed | denied:
            principal = frappe.get_doc("AC Principal", principal)

            sql = ""
            script = ""

            if principal.type == "User" and principal.user:

                sql = frappe.db.escape(f"{principal.user}")

            elif principal.type == "User Group" and principal.user_group:

                sql = frappe.get_all(
                    "User Group Member",
                    filters={"parent": principal.user_group},
                    fields=["user"],
                    distinct=True,
                    order_by="",
                    run=0,
                )

            elif principal.type == "Role" and principal.role:

                if principal.role == "All":
                    sql = frappe.get_all(
                        "User",
                        distinct=True,
                        order_by="",
                        run=0,
                    )
                else:
                    sql = frappe.get_all(
                        "Has Role",
                        filters={"role": principal.role},
                        fields=["parent"],
                        distinct=True,
                        order_by="",
                        run=0,
                    )

            elif principal.type == "User Script" and principal.user_script:

                if principal.script_type == "SQL":
                    sql = principal.user_script
                else:
                    script = principal.user_script

            p = frappe._dict({"name": principal.name})

            if debug:
                p["title"] = principal.get_title()

            if sql:
                p["sql"] = f"`tabUser`.`name` in ({sql})"
            elif script:
                p["script"] = script

            if p.name in denied:
                p["exception"] = 1

            principals.append(p)

        return principals

    def resolve_resources(self, debug=False):

        filters = []

        for row in self.resources:

            query_filter = frappe.get_doc("Query Filter", row.filter)

            r = frappe._dict({"name": query_filter.name})

            if debug:
                r["title"] = query_filter.get_title()
                if query_filter.reference_doctype:
                    r["reference_doctype"] = query_filter.reference_doctype
                if query_filter.reference_report:
                    r["reference_report"] = query_filter.reference_report
                if query_filter.reference_docname:
                    r["reference_docname"] = query_filter.reference_docname
                if query_filter.filters_type:
                    r["filters_type"] = query_filter.filters_type
                if query_filter.filters:
                    r["filters"] = query_filter.filters

            if row.exception:
                r["exception"] = 1

            filters.append(r)

        if not filters:

            filters.append({"all": 1})

        return filters
