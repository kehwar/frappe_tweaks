# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.utils.nestedset import NestedSet, get_ancestors_of, get_descendants_of


class ACRule(Document):

    def before_validate(self):

        self.resource = self.get_root_resource()

    def validate(self):

        if len([p for p in self.principals if not p.exception]) == 0:
            frappe.throw(_("At least one principal must not be an exception."))
        if len([r for r in self.resources if not r.exception]) == 0:
            frappe.throw(_("At least one resource must not be an exception."))
        self.validate_resources_root()

    def validate_resources_root(self):

        root = self.resource

        for r in self.resources:

            if root != get_resource_ancestor(r.resource):
                frappe.throw(_("All resources must belong to the same root resource."))

    def get_root_resource(self):

        return (
            get_resource_ancestor(self.resources[0].resource)
            if self.resources
            else None
        )

    def resolve_principals(self, debug=False):

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

        allowed = set()
        denied = set()

        for r in self.resources:

            resources = [r.resource]
            if r.recursive:
                resources += get_descendants_of(
                    "AC Resource", r.resource, ignore_permissions=1
                )

            if r.exception:
                denied.update(resources)
            else:
                allowed.update(resources)

        allowed = allowed - denied

        resources = []

        for resource in allowed | denied:
            resource = frappe.get_doc("AC Resource", resource)

            r = frappe._dict({"name": resource.name})

            if debug:
                r["title"] = resource.get_title()

            if resource.script_type == "SQL" or not resource.condition_script:
                r["sql"] = resource.condition_script or ""
            else:
                r["script"] = resource.condition_script

            if r.name in denied:
                r["exception"] = 1

            resources.append(r)

        return resources


def get_resource_ancestor(resource):
    ancestors = get_ancestors_of("AC Resource", resource, order_by="lft asc", limit=1)
    return ancestors[0] if ancestors else resource
