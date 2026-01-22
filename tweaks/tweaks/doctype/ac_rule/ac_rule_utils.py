import frappe
from frappe import _, scrub
from frappe.utils.nestedset import rebuild_tree

from tweaks.tweaks.doctype.query_filter.query_filter import get_sql
from tweaks.utils.access_control import allow_value


def has_permissions(doc=None, ptype=None, user=None):

    return not allow_value()


def after_install():

    from tweaks.tweaks.doctype.ac_action.ac_action import setup_standard_actions

    setup_standard_actions()


def clear_ac_rule_cache():
    """
    Clear AC rule cache including rule map and user-rule matching cache.
    """
    frappe.cache.delete_value("ac_rule_map")

    # Clear all user-rule matching cache entries
    # Pattern: ac_rule_user_match:*
    cache = frappe.cache
    if hasattr(cache, "delete_keys"):
        # Redis-based cache supports pattern deletion
        cache.delete_keys("ac_rule_user_match:*")
    else:
        # For other cache backends, we can't easily delete by pattern
        # The cache entries will expire based on TTL
        pass


def clear_ac_rule_user_cache(user=None):
    """
    Clear AC rule user-specific cache.
    Called when user cache is cleared (e.g., when user roles are updated).

    Args:
        user: Username whose cache to clear, or None to clear all user caches
    """
    cache = frappe.cache

    if user:
        # Clear cache for specific user: ac_rule_user_match:*:username
        cache.delete_keys(f"ac_rule_user_match:*:{user}")
    else:
        # Clear all user-rule matching cache entries
        cache.delete_keys("ac_rule_user_match:*")


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


def check_user_matches_rule(rule_name, user, principals):
    """
    Check if a user matches a rule's principal filters.

    Args:
        rule_name: Name of the AC Rule
        user: Username to check
        principals: List of principal filter definitions from rule

    Returns:
        bool: True if user matches the principal filters, False otherwise
    """
    # Get cache TTL
    cache_ttl = get_user_rule_match_cache_ttl()

    # If TTL is 0, caching is disabled
    if cache_ttl == 0:
        return check_user_matches_rule_principals(user, principals)

    # Generate cache key
    cache_key = f"ac_rule_user_match:{rule_name}:{user}"

    # Try to get from cache
    cached_result = frappe.cache.get_value(cache_key)
    if cached_result is not None:
        return cached_result

    # Cache miss - compute the result
    result = check_user_matches_rule_principals(user, principals)

    # Store in cache with TTL
    frappe.cache.set_value(cache_key, result, expires_in_sec=cache_ttl)

    return result


def check_user_matches_rule_principals(user, principals):
    """
    Check if user matches principal filters.

    Args:
        user: Username to check
        principals: List of principal filter definitions from rule

    Returns:
        bool: True if user matches the principal filters, False otherwise
    """
    # Build SQL query to check if user matches principals
    allowed = [
        get_principal_filter_sql(r, user=user)
        for r in principals
        if r.get("exception", 0) == 0
    ]
    denied = [
        get_principal_filter_sql(r, user=user)
        for r in principals
        if r.get("exception", 0) == 1
    ]

    allowed = [r for r in allowed if r]
    denied = [r for r in denied if r]

    if not allowed:
        return False

    allowed_sql = (
        " OR ".join([f"({q})" for q in allowed]) if len(allowed) != 1 else allowed[0]
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


def get_rule_map():
    # Early returns for system states
    if frappe.flags.in_patch and not frappe.db.table_exists("AC Rule"):
        return {}

    if frappe.flags.in_install:
        return {}

    if frappe.flags.in_migrate:
        return {}

    # Check cache first
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

        principals = rule.resolve_principals()
        if len(principals) == 0:
            frappe.log_error(f"AC Rule {rule.name} has no valid principals")
            continue

        resources = rule.resolve_resources()
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
                    "type": rule.type,
                    "principals": principals,
                    "resources": resources,
                }
            )

            folder.setdefault(action, []).append(r)

    # Cache the rule map
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


def get_principal_filter_sql(filter, user=None):

    if filter.get("name"):
        filter = frappe.get_cached_doc("Query Filter", filter.get("name"))

    sql = get_sql(filter, user=user)
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


def get_resource_rules(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, type, key, fieldname, action, user
    )

    rule_map = get_rule_map()

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
        if check_user_matches_rule(rule_name, user, principals):
            rules.append(rule)

    return frappe._dict({"rules": rules})


def get_resource_filter_sql(filter, user=None):

    if filter.get("all"):
        return "1=1"

    if filter.get("name"):
        filter = frappe.get_cached_doc("Query Filter", filter.get("name"))
        return get_sql(filter, user=user)

    return "1=0"


def get_resource_filter_query(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, type, key, fieldname, action, user
    )

    rule_map = get_resource_rules(
        resource, doctype, report, type, key, fieldname, action, user
    )

    if rule_map.get("unmanaged"):
        return {"query": "", "unmanaged": True, "access": "total"}

    folder = rule_map.get("rules", [])

    resource_filter_queries = []
    for rule in folder:

        allowed = [
            get_resource_filter_sql(r, user=user)
            for r in rule.get("resources")
            if r.get("exception", 0) == 0
        ]
        denied = [
            get_resource_filter_sql(r, user=user)
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

    return frappe._dict({"query": resource_filter_query, "access": access})


def get_allowed_docs_query(doctype, action="read"):

    conditions = _get_permission_query_conditions_for_doctype(
        doctype=doctype, action=action
    )

    if not conditions:
        return f"SELECT `tab{doctype}`.`name` FROM `tab{doctype}`"

    return f"SELECT `tab{doctype}`.`name` FROM `tab{doctype}` WHERE {conditions}"


def has_resource_access(
    resource="",
    doctype="",
    report="",
    type="",
    key="",
    fieldname="",
    action="",
    user="",
):

    type, key, fieldname, action, user = get_params(
        resource, doctype, report, type, key, fieldname, action, user
    )

    rule_map = get_resource_rules(
        resource, doctype, report, type, key, fieldname, action, user
    )

    if rule_map.get("unmanaged"):
        return {"access": True, "unmanaged": True}

    folder = rule_map.get("rules", [])

    access = len(folder) > 0

    return frappe._dict({"access": access})


def has_ac_permission(
    docname="",
    doctype="",
    action="",
    user="",
):
    """
    Check if a user has AC Rules permission for a specific document and action.

    This function generates SQL to verify if a specific document matches the AC Rules
    for the given user and action, then executes it to determine permission.

    Args:
        docname: Document name
        doctype: DocType name
        action: Action name (e.g., "read", "write", "approve", "reject")
        user: User name (defaults to current user)

    Returns:
        bool: True if user has permission, False otherwise
    """
    user = user or frappe.session.user

    # Administrator always has full access
    if user == "Administrator":
        return True

    # Validate required parameters
    if not docname or not doctype:
        frappe.throw(_("docname and doctype are required"))
    if not action:
        frappe.throw(_("Action is required"))

    # Normalize action name
    action = scrub(action)

    # Get filter query from AC Rules
    result = get_resource_filter_query(doctype=doctype, action=action, user=user)

    # If unmanaged, return True (fall through to standard Frappe permissions)
    if result.get("unmanaged"):
        return True

    # If no access at all, return False
    if result.get("access") == "none":
        return False

    # If total access, return True
    if result.get("access") == "total":
        return True

    # Partial access - need to check if this specific document matches the filter
    query = result.get("query", "")
    if not query:
        return False

    # Execute SQL to check if this document matches the AC Rules filter
    sql = f"""
        SELECT COUNT(*) as count
        FROM `tab{doctype}`
        WHERE `tab{doctype}`.`name` = {frappe.db.escape(docname)}
        AND ({query})
    """

    query_result = frappe.db.sql(sql, as_dict=True)
    has_access = query_result[0].get("count", 0) > 0 if query_result else False

    return has_access


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
    result = get_resource_filter_query(doctype=doctype, action=action, user=user)

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
