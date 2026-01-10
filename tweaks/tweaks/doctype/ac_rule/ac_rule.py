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
        if hasattr(super(), "clear_cache"):
            super().clear_cache()
        from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import clear_ac_rule_cache

        clear_ac_rule_cache()

    def on_trash(self):
        """Clear AC rule cache when rule is deleted"""
        if hasattr(super(), "on_trash"):
            super().on_trash()
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

    def resolve_principals(self):

        filters = []

        for row in self.principals:

            query_filter = frappe.get_doc("Query Filter", row.filter)

            r = frappe._dict(
                {
                    "name": query_filter.name,
                    "doctype": query_filter.reference_doctype,
                }
            )

            if row.exception:
                r["exception"] = 1

            filters.append(r)

        return filters

    def resolve_principals_deprecated(self):

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

            if sql:
                p["sql"] = f"`tabUser`.`name` in ({sql})"
            elif script:
                p["script"] = script

            if p.name in denied:
                p["exception"] = 1

            principals.append(p)

        return principals

    def resolve_resources(self):

        filters = []

        for row in self.resources:

            query_filter = frappe.get_doc("Query Filter", row.filter)

            r = frappe._dict({"name": query_filter.name})

            if row.exception:
                r["exception"] = 1

            filters.append(r)

        if not filters:

            filters.append({"all": 1})

        return filters

    def get_distinct_query_filters(self, query_filters):
        """
        Helper function that creates distinct tuples from query filters.
        
        For each non-exception filter, creates a tuple containing:
        - The rule type (Permit or Forbid)
        - The non-exception filter
        - A tuple of all exception filters
        
        Args:
            query_filters: List of filter rows (principals or resources child table)
            
        Returns:
            List of tuples: [(rule_type, non_exception_filter, (exception_filters...))]
        
        Example:
            If Rule is Permit, and filters are allow1, allow2, allow3, forbid1, forbid2
            Returns:
            [
                ("Permit", "allow1", ("forbid1", "forbid2")),
                ("Permit", "allow2", ("forbid1", "forbid2")),
                ("Permit", "allow3", ("forbid1", "forbid2"))
            ]
        """
        # Separate non-exception and exception filters
        non_exception_filters = []
        exception_filters = []
        
        for row in query_filters:
            if row.exception:
                exception_filters.append(row.filter)
            else:
                non_exception_filters.append(row.filter)
        
        # Create tuples for each non-exception filter
        result = []
        exception_tuple = tuple(sorted(exception_filters))
        
        for filter_name in non_exception_filters:
            result.append((self.type, filter_name, exception_tuple))
        
        return result

    def get_distinct_principal_query_filters(self):
        """
        Get distinct tuples for principal filters.
        
        Returns:
            List of tuples: [(rule_type, non_exception_filter, (exception_filters...))]
        """
        return self.get_distinct_query_filters(self.principals)

    def get_distinct_resource_query_filters(self):
        """
        Get distinct tuples for resource filters.
        
        Returns:
            List of tuples: [(rule_type, non_exception_filter, (exception_filters...))]
        """
        return self.get_distinct_query_filters(self.resources)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_query_filters_for_resource(doctype, txt, searchfield, start, page_len, filters):
    """
    Query method to filter Query Filters based on the selected AC Resource.
    Only returns Query Filters that match the resource's doctype or report.
    """
    resource_name = filters.get("resource")

    if not resource_name:
        return []

    resource = frappe.get_cached_doc("AC Resource", resource_name)

    query_filter_filters = {}

    # If resource is based on DocType, filter Query Filters by reference_doctype
    if resource.type == "DocType" and resource.document_type:
        query_filter_filters["reference_doctype"] = resource.document_type

    # If resource is based on Report, filter Query Filters by reference_report
    elif resource.type == "Report" and resource.report:
        query_filter_filters["reference_report"] = resource.report

    # Add text search if provided
    if txt:
        query_filter_filters["filter_name"] = ["like", f"%{txt}%"]

    return frappe.get_all(
        "Query Filter",
        filters=query_filter_filters,
        fields=["name", "filter_name"],
        or_filters=(
            {"name": ["like", f"%{txt}%"], "filter_name": ["like", f"%{txt}%"]}
            if txt
            else None
        ),
        start=start,
        page_length=page_len,
        order_by="filter_name asc",
        as_list=True,
    )
