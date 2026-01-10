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


def clear_ac_rule_cache():
    """
    Clear AC rule cache including rule map and user-rule matching cache.
    """
    frappe.cache.delete_value("ac_rule_map")
    
    # Clear all user-rule matching cache entries
    # Pattern: ac_rule_user_match:*
    cache = frappe.cache
    if hasattr(cache, 'delete_keys'):
        # Redis-based cache supports pattern deletion
        cache.delete_keys("ac_rule_user_match:*")
    else:
        # For other cache backends, we can't easily delete by pattern
        # The cache entries will expire based on TTL
        pass


def get_user_rule_match_cache_ttl():
    """
    Get the cache TTL for user-rule matching from AC Settings.
    Returns TTL in seconds (converted from minutes).
    """
    try:
        if not frappe.db.table_exists("AC Settings"):
            return 300  # Default 5 minutes
            
        settings = frappe.get_cached_doc("AC Settings", "AC Settings")
        ttl_minutes = settings.get("user_rule_match_cache_ttl", 5)
        
        # Convert minutes to seconds, 0 means no caching
        return ttl_minutes * 60 if ttl_minutes else 0
    except Exception:
        # Default to 5 minutes if any error
        return 300


def check_user_matches_rule(rule_name, user, principals, debug=False):
    """
    Check if a user matches a rule's principal filters.
    
    Args:
        rule_name: Name of the AC Rule
        user: Username to check
        principals: List of principal filter definitions from rule
        debug: If True, skip caching
    
    Returns:
        bool: True if user matches the principal filters, False otherwise
    """
    # Skip caching in debug mode
    if debug:
        return check_user_matches_rule_principals(user, principals, debug=debug)
    
    # Get cache TTL
    cache_ttl = get_user_rule_match_cache_ttl()
    
    # If TTL is 0, caching is disabled
    if cache_ttl == 0:
        return check_user_matches_rule_principals(user, principals, debug=debug)
    
    # Generate cache key
    cache_key = f"ac_rule_user_match:{rule_name}:{user}"
    
    # Try to get from cache
    cached_result = frappe.cache.get_value(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Cache miss - compute the result
    result = check_user_matches_rule_principals(user, principals, debug=debug)
    
    # Store in cache with TTL
    frappe.cache.set_value(cache_key, result, expires_in_sec=cache_ttl)
    
    return result


def check_user_matches_rule_principals(user, principals, debug=False):
    """
    Check if user matches principal filters.
    
    Args:
        user: Username to check
        principals: List of principal filter definitions from rule
        debug: If True, enables debug output
    
    Returns:
        bool: True if user matches the principal filters, False otherwise
    """
    # Build SQL query to check if user matches principals
    allowed = [
        get_principal_filter_sql(r)
        for r in principals
        if r.get("exception", 0) == 0
    ]
    denied = [
        get_principal_filter_sql(r)
        for r in principals
        if r.get("exception", 0) == 1
    ]
    
    allowed = [r for r in allowed if r]
    denied = [r for r in denied if r]
    
    if not allowed:
        return False
    
    allowed_sql = (
        " OR ".join([f"({q})" for q in allowed])
        if len(allowed) != 1
        else allowed[0]
    )
    denied_sql = (
        " OR ".join([f"({q})" for q in denied]) if len(denied) != 1 else denied[0]
    )
    
    if allowed_sql and denied_sql:
        user_filter_sql = f"({allowed_sql}) AND NOT ({denied_sql})"
    elif allowed_sql:
        user_filter_sql = f"{allowed_sql}"
    else:
        return False
    
    # Execute query to check if user matches
    query = f"""
        SELECT COUNT(*) as count
        FROM `tabUser`
        WHERE `tabUser`.`name` = {frappe.db.escape(user)}
        AND ({user_filter_sql})
    """
    
    result = frappe.db.sql(query, as_dict=True)
    return result[0].get("count", 0) > 0 if result else False


@frappe.whitelist()
def get_rule_map(debug=False):
    # Early returns for system states
    if frappe.flags.in_patch and not frappe.db.table_exists("AC Rule"):
        return {}

    if frappe.flags.in_install:
        return {}

    if frappe.flags.in_migrate:
        return {}

    # Check cache first (skip cache if debug mode)
    if not debug:
        rule_map = frappe.cache.get_value("ac_rule_map")
        if rule_map is not None:
            return rule_map

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

    # Cache the rule map (skip cache if debug mode)
    if not debug:
        frappe.cache.set_value("ac_rule_map", rule_map)

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

    # Filter rules to those that match the user using cached function
    rules = []
    for rule in folder:
        rule_name = rule.get("name")
        principals = rule.get("principals", [])
        
        # Use cached function to check if user matches this rule
        if check_user_matches_rule(rule_name, user, principals, debug=debug):
            rules.append(rule)

    if debug:
        # In debug mode, also include the old query structure for comparison
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


def _get_permission_query_conditions_for_doctype(doctype, user=None, action="read"):
    """
    Internal helper to get permission query conditions for a specific action.

    Args:
        doctype: DocType name
        user: User name (defaults to current user)
        action: Action name (e.g., "read", "Write", "Create", etc.)

    Returns:
        str: SQL WHERE clause or empty string if unmanaged/full access
    """

    user = user or frappe.session.user

    # Administrator always has full access
    if user == "Administrator":
        return ""

    # Get filter query from AC Rules
    result = get_resource_filter_query(
        doctype=doctype, action=action, user=user, debug=False
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


def get_permission_query_conditions(user=None, doctype=None):
    """
    Hook for Frappe's permission_query_conditions.
    Returns SQL WHERE clause to filter records based on AC Rules.

    This is called by Frappe to filter list views and queries for read/select operations.

    Args:
        user: User name (defaults to current user)
        doctype: DocType name

    Returns:
        str: SQL WHERE clause or empty string if unmanaged/full access
    """
    return _get_permission_query_conditions_for_doctype(doctype, user, action="read")


def get_write_permission_query_conditions(user=None, doctype=None, ptype=None):
    """
    Hook for Frappe's write_permission_query_conditions.
    Returns SQL WHERE clause to filter records based on AC Rules for write operations.

    This is called by Frappe to filter queries for write operations (write, create, submit, cancel, delete).

    Args:
        user: User name (defaults to current user)
        doctype: DocType name
        ptype: Permission type (write, create, submit, cancel, delete)

    Returns:
        str: SQL WHERE clause or empty string if unmanaged/full access
    """
    # Map ptype to AC Action using scrub
    action = scrub(ptype or "write")
    return _get_permission_query_conditions_for_doctype(doctype, user, action=action)
