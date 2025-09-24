import frappe
from frappe import _, scrub
from frappe.utils.nestedset import rebuild_tree

from tweaks.tweaks.doctype.ac_principal.ac_principal import (
    run_script as run_principal_script,
)
from tweaks.tweaks.doctype.ac_resource.ac_resource import (
    run_script as run_resource_script,
)
from tweaks.utils.access_control import allow_value


def has_permissions(doc=None, ptype=None, user=None, debug=False):

    return not allow_value()


def after_install():

    from tweaks.tweaks.doctype.ac_action.ac_action import insert_standard_actions

    insert_standard_actions()


@frappe.whitelist()
def get_rule_map(debug=False):

    rebuild_tree("AC Principal")
    rebuild_tree("AC Resource")

    rules = frappe.get_all(
        "AC Rule",
        filters=[["disabled", "=", 0]],
        fields=["name", "valid_from", "valid_upto"],
    )
    rules = [
        r
        for r in rules
        if (not r.valid_from or r.valid_from <= frappe.utils.getdate())
        and (not r.valid_upto or r.valid_upto >= frappe.utils.getdate())
    ]

    rule_map = {}

    resources = frappe.get_all(
        "AC Resource",
        fields=[
            "name",
            "type",
            "document_type",
            "report",
            "custom",
            "fieldname",
            "managed_actions",
        ],
        filters=[["disabled", "=", 0], ["type", "in", ("DocType", "Report", "Custom")]],
    )
    all_actions = frappe.get_all(
        "AC Action", filters=[["disabled", "=", 0]], pluck="name"
    )
    for r in resources:
        folder = (
            rule_map.setdefault(scrub(r.type), {})
            .setdefault(r.document_type or r.report or r.custom, {})
            .setdefault(r.fieldname or "", {})
        )
        if r.managed_actions == "Select":
            actions = frappe.get_all(
                "AC Resource Action", filters={"parent": r.name}, pluck="action"
            )
            actions = [a for a in actions if a in all_actions]
        else:
            actions = all_actions
        for action in actions:
            folder.setdefault(scrub(action), [])

    for r in rules:

        rule = frappe.get_doc("AC Rule", r.name)
        resource = rule.resource
        resource = frappe.get_doc("AC Resource", resource)

        folder = (
            rule_map.get(scrub(resource.type), {})
            .get(resource.document_type or resource.report or resource.custom, {})
            .get(resource.fieldname or "", None)
        )
        if folder is None:
            frappe.log_error(
                f"AC Rule {rule.name} has invalid root resource {resource.name}"
            )
            continue

        actions = [scrub(a.action) for a in rule.actions]

        principals = rule.resolve_principals(debug=debug)
        if len(principals) == 0:
            frappe.log_error(f"AC Rule {rule.name} has no valid principals")
            continue

        resources = rule.resolve_resources(debug=debug)
        if len(resources) == 0:
            frappe.log_error(f"AC Rule {rule.name} has no valid resources")
            continue

        for action in actions:

            if action not in folder:
                frappe.log_error(
                    f"AC Rule {rule.name} has invalid action {action} for resource {resource.name}"
                )
                continue

            r = frappe._dict(
                {
                    "name": rule.name,
                    "title": rule.get_title(),
                    "type": rule.type,
                    "principals": principals,
                    "resources": resources,
                }
            )

            if not (debug):
                r.pop("title")

            folder.setdefault(action, []).append(r)

    return rule_map


def get_params(
    resource="",
    doctype="",
    report="",
    custom="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
):

    if not key or not type:

        if resource:
            if isinstance(resource, str):
                resource = frappe.get_doc("AC Resource", resource)
            type = scrub(resource.type)
            key = resource.document_type or resource.report or resource.custom
            fieldname = resource.fieldname or ""
        elif report:
            type = "report"
            key = report
        elif doctype:
            type = "doctype"
            key = doctype
        elif custom:
            type = "custom"
            key = custom
        else:
            type = scrub(type)
            key = doctype or report or custom

    if not key or not type:
        frappe.throw(
            _("Resource or (Type and Document Type/Report/Custom) is required")
        )

    action = scrub(action) or "read"

    user = user or frappe.session.user

    return type, key, fieldname, action, user


def get_principal_condition(condition):
    if condition.get("script"):
        return run_principal_script(condition.get("script"), condition.get("name"))
    return condition.get("sql", "")


@frappe.whitelist()
def get_resource_rules(
    resource="",
    doctype="",
    report="",
    custom="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
    debug=False,
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, custom, type, key, fieldname, action, user
    )

    if debug or user != frappe.session.user:
        frappe.only_for("System Manager")

    rule_map = get_rule_map(debug)

    folder = (
        rule_map.get(type, {}).get(key, {}).get(fieldname or "", {}).get(action, None)
    )

    if folder is None:
        return {"rules": [], "unmanaged": True}

    user_filter_queries = []
    for rule in folder:

        rule_name = rule.get("name")

        allowed = [
            get_principal_condition(r)
            for r in rule.get("principals", [])
            if r.get("exception", 0) == 0
        ]
        denied = [
            get_principal_condition(r)
            for r in rule.get("principals", [])
            if r.get("exception", 0) == 1
        ]

        allowed = [r for r in allowed if r]
        denied = [r for r in denied if r]

        allowed = (
            " OR ".join([f"({q})" for q in allowed])
            if len(allowed) != 1
            else allowed[0]
        )
        denied = (
            " OR ".join([f"({q})" for q in denied]) if len(denied) != 1 else denied[0]
        )

        q = {"rule": rule_name}

        if allowed and denied:
            user_filter_queries.append(q | {"sql": f"({allowed}) AND NOT ({denied})"})
        elif allowed:
            user_filter_queries.append(q | {"sql": f"{allowed}"})
        else:
            frappe.log_error(f"AC Rule {rule_name} has no valid principals")

    user_filter_query = " UNION ".join(
        [
            f"""SELECT {frappe.db.escape(q.get('rule'))} AS "rule" FROM `tabUser` WHERE `tabUser`.`name` = {frappe.db.escape(user)} AND ({q.get("sql")})"""
            for q in user_filter_queries
        ]
    )
    if user_filter_query:
        rules = frappe.db.sql(user_filter_query, pluck="rule")
        rules = [r for r in folder if r.get("name") in rules]
    else:
        rules = []

    if debug:

        return frappe._dict(
            {
                "type": type,
                "key": key,
                "fieldname": fieldname,
                "action": action,
                "user": user,
                "rules": rules,
                "query": {
                    "query": user_filter_query,
                    "parts": user_filter_queries,
                },
                "folder": folder,
            }
        )

    return frappe._dict({"rules": rules})


def get_resource_condition(condition):
    if condition.get("script"):
        return run_resource_script(condition.get("script"), condition.get("name"))
    return condition.get("sql", "") or "1=1"


@frappe.whitelist()
def get_resource_filter_query(
    resource="",
    doctype="",
    report="",
    custom="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
    debug=False,
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, custom, type, key, fieldname, action, user
    )

    rule_map = get_resource_rules(
        resource, doctype, report, custom, type, key, fieldname, action, user, debug
    )

    if rule_map.get("unmanaged"):
        return {"query": "", "unmanaged": True, "access": "total"}

    folder = rule_map.get("rules", [])

    resource_filter_queries = []
    for rule in folder:

        allowed = [
            get_resource_condition(r)
            for r in rule.get("resources")
            if r.get("exception", 0) == 0
        ]
        denied = [
            get_resource_condition(r)
            for r in rule.get("resources")
            if r.get("exception", 0) == 1
        ]

        allowed = (
            " OR ".join([f"({q})" for q in allowed])
            if len(allowed) != 1
            else allowed[0]
        )
        denied = (
            " OR ".join([f"({q})" for q in denied]) if len(denied) != 1 else denied[0]
        )

        q = {"rule": rule.get("name"), "type": rule.get("type")}

        if allowed and denied:
            resource_filter_queries.append(
                q | {"sql": f"({allowed}) AND NOT ({denied})"}
            )
        elif allowed:
            resource_filter_queries.append(q | {"sql": f"{allowed}"})
        elif denied:
            resource_filter_queries.append(q | {"sql": f"NOT ({denied})"})
        else:
            frappe.log_error(
                f"AC Rule {rule.get('name')} has no valid resource conditions"
            )

    allowed = [
        r.get("sql") for r in resource_filter_queries if r.get("type") == "Permit"
    ]
    denied = [
        r.get("sql") for r in resource_filter_queries if r.get("type") == "Forbid"
    ]

    allowed = (
        " OR ".join([f"({q})" for q in allowed]) if len(allowed) != 1 else allowed[0]
    )
    denied = " OR ".join([f"({q})" for q in denied]) if len(denied) != 1 else denied[0]

    if allowed and denied:
        resource_filter_query = f"({allowed}) AND NOT ({denied})"
    elif allowed:
        resource_filter_query = f"{allowed}"
    else:
        resource_filter_query = "1=0"

    if resource_filter_query == "1=1":
        access = "total"
    elif resource_filter_query == "1=0":
        access = "none"
    else:
        access = "partial"

    if debug:

        return frappe._dict(
            {
                "type": type,
                "key": key,
                "fieldname": fieldname,
                "action": action,
                "user": user,
                "query": resource_filter_query,
                "access": access,
                "parts": resource_filter_queries,
                "folder": folder,
            }
        )

    return frappe._dict({"query": resource_filter_query, "access": access})


@frappe.whitelist()
def has_resource_access(
    resource="",
    doctype="",
    report="",
    custom="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
    debug=False,
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, custom, type, key, fieldname, action, user
    )

    rule_map = get_resource_rules(
        resource, doctype, report, custom, type, key, fieldname, action, user, debug
    )

    if rule_map.get("unmanaged"):
        return {"access": True, "unmanaged": True}

    folder = rule_map.get("rules", [])

    access = len(folder) > 0

    if debug:

        return frappe._dict(
            {
                "type": type,
                "key": key,
                "fieldname": fieldname,
                "action": action,
                "user": user,
                "folder": folder,
                "access": access,
            }
        )

    return frappe._dict({"access": access})
