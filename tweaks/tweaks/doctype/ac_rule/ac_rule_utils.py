import frappe
from frappe import _, scrub
from frappe.utils.nestedset import rebuild_tree

from tweaks.tweaks.doctype.query_filter.query_filter import get_sql
from tweaks.utils.access_control import allow_value


def has_permissions(doc=None, ptype=None, user=None, debug=False):

    return not allow_value()


def after_install():

    from tweaks.tweaks.doctype.ac_action.ac_action import insert_standard_actions

    insert_standard_actions()


@frappe.whitelist()
def get_rule_map(debug=False):

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
            "document_type",
            "report",
            "fieldname",
            "managed_actions",
        ],
        filters=[["disabled", "=", 0]],
    )
    all_actions = frappe.get_all(
        "AC Action", filters=[["disabled", "=", 0]], pluck="name"
    )
    for r in resources:
        if r.document_type:
            r.type = "DocType"
        elif r.report:
            r.type = "Report"
        folder = (
            rule_map.setdefault(scrub(r.type), {})
            .setdefault(r.document_type or r.report, {})
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
            .get(resource.document_type or resource.report, {})
            .get(resource.fieldname or "", None)
        )
        if folder is None:
            frappe.log_error(
                f"AC Rule {rule.name} has invalid resource {resource.name}"
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
            key = resource.document_type or resource.report
            fieldname = resource.fieldname or ""
        elif report:
            type = "report"
            key = report
        elif doctype:
            type = "doctype"
            key = doctype
        else:
            type = scrub(type)
            key = doctype or report

    if not key or not type:
        frappe.throw(_("Resource or (Type and Document Type/Report) is required"))

    action = scrub(action) or "read"

    user = user or frappe.session.user

    return type, key, fieldname, action, user


def get_principal_filter_sql(filter):

    if filter.get("name"):
        filter = frappe.get_cached_doc("Query Filter", filter.get("name"))

    sql = filter.get_sql()
    if filter.get("reference_doctype") == "User":
        return sql
    if filter.get("reference_doctype") == "User Group":
        user_groups = frappe.db.sql(
            f"SELECT `name`FROM `tabUser Group` WHERE {sql}", pluck="name"
        )
        sql = frappe.get_all(
            "User Group Member",
            filters={"parent": ["in", user_groups]},
            fields=["user"],
            distinct=True,
            order_by="",
            run=0,
        )
        return f"`tabUser`.`name` in ({sql})"
    if filter.get("reference_doctype") == "Role":
        roles = frappe.db.sql(f"SELECT `name`FROM `tabRole` WHERE {sql}", pluck="name")
        if "All" in roles:
            sql = frappe.get_all(
                "User",
                distinct=True,
                order_by="",
                run=0,
            )
        else:
            sql = frappe.get_all(
                "Has Role",
                filters={"role": ["in", roles]},
                fields=["parent"],
                distinct=True,
                order_by="",
                run=0,
            )
        return f"`tabUser`.`name` in ({sql})"
    return ""


@frappe.whitelist()
def get_resource_rules(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
    debug=False,
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, type, key, fieldname, action, user
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
            get_principal_filter_sql(r)
            for r in rule.get("principals", [])
            if r.get("exception", 0) == 0
        ]
        denied = [
            get_principal_filter_sql(r)
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


def get_resource_filter_sql(filter):

    if filter.get("all"):
        return "1=1"

    if filter.get("name"):
        filter = frappe.get_cached_doc("Query Filter", filter.get("name"))
        return filter.get_sql()

    return "1=0"


@frappe.whitelist()
def get_resource_filter_query(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
    debug=False,
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, type, key, fieldname, action, user
    )

    rule_map = get_resource_rules(
        resource, doctype, report, type, key, fieldname, action, user, debug
    )

    if rule_map.get("unmanaged"):
        return {"query": "", "unmanaged": True, "access": "total"}

    folder = rule_map.get("rules", [])

    resource_filter_queries = []
    for rule in folder:

        allowed = [
            get_resource_filter_sql(r)
            for r in rule.get("resources")
            if r.get("exception", 0) == 0
        ]
        denied = [
            get_resource_filter_sql(r)
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
                "user_filter_query": rule_map.get("query"),
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
    type="",
    key="",
    fieldname="",
    action="",
    user="",
    debug=False,
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, type, key, fieldname, action, user
    )

    rule_map = get_resource_rules(
        resource, doctype, report, type, key, fieldname, action, user, debug
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


def get_permission_query_conditions(doctype, user=None):
    """
    Hook for Frappe's permission_query_conditions.
    Returns SQL WHERE clause to filter records based on AC Rules.
    
    This is called by Frappe to filter list views and queries.
    
    Args:
        doctype: DocType name
        user: User name (defaults to current user)
    
    Returns:
        str: SQL WHERE clause or empty string if unmanaged/full access
    """
    # Administrator always has full access
    if user == "Administrator" or frappe.session.user == "Administrator":
        return ""
    
    user = user or frappe.session.user
    
    # Default action for listing is "read"
    action = "read"
    
    # Get filter query from AC Rules
    result = get_resource_filter_query(
        doctype=doctype,
        action=action,
        user=user,
        debug=False
    )
    
    # If unmanaged, return empty string (fall through to standard Frappe permissions)
    if result.get("unmanaged"):
        return ""
    
    # If no access, return impossible condition
    if result.get("access") == "none":
        return "1=0"
    
    # If total access, return empty string
    if result.get("access") == "total":
        return ""
    
    # Return the filter query
    query = result.get("query", "")
    return query if query else ""


def has_permission(doc, ptype=None, user=None, debug=False):
    """
    Hook for Frappe's has_permission.
    Checks if user has permission to access a specific document.
    
    This is called by Frappe for single document permission checks.
    
    Args:
        doc: Document object or dict with doctype and name
        ptype: Permission type (read, write, create, delete, submit, cancel, etc.)
        user: User name (defaults to current user)
        debug: Debug mode flag
    
    Returns:
        bool or None: True if allowed, False if denied, None if unmanaged
    """
    # Administrator always has full access
    if user == "Administrator" or frappe.session.user == "Administrator":
        return True
    
    user = user or frappe.session.user
    
    # Extract doctype from doc
    if isinstance(doc, dict):
        doctype = doc.get("doctype")
    else:
        doctype = doc.doctype
    
    # Map ptype to AC Action - capitalize first letter to match AC Action naming
    action = (ptype or "read").capitalize()
    
    # Get rules for this resource/action/user
    result = get_resource_rules(
        doctype=doctype,
        action=scrub(action),
        user=user,
        debug=False
    )
    
    # If unmanaged, return None (fall through to standard Frappe permissions)
    if result.get("unmanaged"):
        return None
    
    rules = result.get("rules", [])
    
    # If no rules, deny access
    if not rules:
        return False
    
    # Get document name
    if isinstance(doc, dict):
        doc_name = doc.get("name")
    else:
        doc_name = doc.name
    
    # If doc is new (no name yet), check if Create action is allowed
    if not doc_name and ptype == "create":
        # Has rules for create action, so allow
        return True
    
    # For existing documents, check if document matches any rule's resource filters
    if doc_name:
        # Build query to check if document matches any rule
        resource_filter_queries = []
        
        for rule in rules:
            allowed = [
                get_resource_filter_sql(r)
                for r in rule.get("resources", [])
                if r.get("exception", 0) == 0
            ]
            denied = [
                get_resource_filter_sql(r)
                for r in rule.get("resources", [])
                if r.get("exception", 0) == 1
            ]
            
            allowed = (
                " OR ".join([f"({q})" for q in allowed])
                if len(allowed) != 1
                else (allowed[0] if allowed else "")
            )
            denied = (
                " OR ".join([f"({q})" for q in denied])
                if len(denied) != 1
                else (denied[0] if denied else "")
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
        
        # Separate Permit and Forbid rules
        permit_queries = [
            r.get("sql") for r in resource_filter_queries if r.get("type") == "Permit"
        ]
        forbid_queries = [
            r.get("sql") for r in resource_filter_queries if r.get("type") == "Forbid"
        ]
        
        # Build final query
        permit_sql = (
            " OR ".join([f"({q})" for q in permit_queries])
            if len(permit_queries) != 1
            else (permit_queries[0] if permit_queries else "")
        )
        forbid_sql = (
            " OR ".join([f"({q})" for q in forbid_queries])
            if len(forbid_queries) != 1
            else (forbid_queries[0] if forbid_queries else "")
        )
        
        # Check if document matches filters
        if permit_sql or forbid_sql:
            check_sql = f"""
                SELECT COUNT(*) 
                FROM `tab{doctype}` 
                WHERE `tab{doctype}`.`name` = %s
            """
            
            if permit_sql and forbid_sql:
                check_sql += f" AND ({permit_sql}) AND NOT ({forbid_sql})"
            elif permit_sql:
                check_sql += f" AND ({permit_sql})"
            elif forbid_sql:
                check_sql += f" AND NOT ({forbid_sql})"
            
            count = frappe.db.sql(check_sql, (doc_name,))[0][0]
            return count > 0
        else:
            # No filters means all records are allowed (if we have permit rules)
            has_permit = any(r.get("type") == "Permit" for r in rules)
            return has_permit
    
    # Default: if we have rules, allow (they passed principal checks)
    return True
