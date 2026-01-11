# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub

from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import (
    check_user_matches_rule_principals,
    get_principal_filter_sql,
)


def execute(filters=None):
    """
    AC Resource Rules Report

    Shows which users have access to which resources based on resource query filters.

    Filters:
        - resource (required): AC Resource to analyze
        - query_filter (optional): Query Filter for principal filtering (User, User Group, Role, or Role Profile)
        - action (optional): Specific action to check (shows Y/N instead of listing all actions)
        - pivot (optional, default=0): If checked, pivot filters to columns (matrix view); if unchecked, show as flat table

    Report Structure (when pivot=0, default):
        - Flat table with columns: Principal User, Resource Query Filter, Actions
        - Each row represents a user + filter combination where the user has access

    Report Structure (when pivot=1):
        - Matrix view:
          - Rows: Principal Users (all enabled, or filtered by Query Filter)
          - Columns: Resource Query Filters from AC Rules (grouped and de-duplicated)
          - Cells: Y/N if action filter is specified, or comma-separated sorted actions if not

    Column Logic (pivot mode):
        - Columns are deduplicated by (rule_type, non_exception_filter, exception_filters)
        - Same filter can appear in multiple columns if used by different rule types (Permit vs Forbid)
        - Each non-exception resource filter becomes a column
        - Exception filters multiply columns (e.g., "Allow1 - ⚠️ Forbid1, ⚠️ Forbid2")
        - Actions from multiple rules sharing the same filter combination are aggregated (deduplicated)
          and sorted alphabetically in that column
        - Column labels show filter names with emoji (✅ Permit, 🚫 Forbid based on rule type; ⚠️ for exception filters)
        - Columns are sorted alphabetically by their final label

    Cell Logic:
        - For each user/filter column combination:
          1. Check if user matches principal filters of each rule in that column
             (Principal logic: (M1 OR M2) AND NOT (E1 OR E2) where M = main filters, E = exception filters)
          2. If user matches, include that rule's actions in the cell
          3. Aggregate and sort all matched actions
        - If action filter is specified: show "Y" if user has that action, "N" otherwise (hidden in UI)
        - If no action filter: show comma-separated list of all actions user has for that resource filter

    The report evaluates each user against principal filters to determine who has access,
    then shows which resource filters apply for each user.
    Only enabled rules within valid date ranges are shown.
    """
    columns = []
    data = []

    if not filters or not filters.get("resource"):
        return columns, data

    columns, data = get_data(filters)
    return columns, data


def get_data(filters):
    """
    Get permission data for the selected resource.

    Process:
    1. Fetch AC Resource and related AC Rules (enabled, within valid date range)
    2. Get users (all enabled or filtered by Query Filter)
    3. Build flat array of (User, Distinct Resource Query Filter, Actions)
    4. If pivot=1, transform to matrix view; if pivot=0, return flat table

    Returns:
        Tuple of (columns, data) where:
        - columns: List of column definitions for the report table
        - data: List of row dicts with user info and permission data
    """

    resource_name = filters.get("resource")
    query_filter_name = filters.get("query_filter")
    pivot = filters.get("pivot", 0)

    # Get the AC Resource
    resource = frappe.get_doc("AC Resource", resource_name)

    # Get all AC Rules for this resource
    ac_rules = frappe.get_all(
        "AC Rule",
        filters={
            "resource": resource_name,
            "disabled": 0,
        },
        fields=["name", "title", "type", "valid_from", "valid_upto"],
        order_by="name",
    )

    # Filter rules by valid date range
    ac_rules = [
        r
        for r in ac_rules
        if (not r.valid_from or r.valid_from <= frappe.utils.getdate())
        and (not r.valid_upto or r.valid_upto >= frappe.utils.getdate())
    ]

    if not ac_rules:
        return [], []

    # Get all users (or filtered users if query filter is provided)
    users = get_users(query_filter_name)

    if not users:
        return [], []

    # Build filter columns by analyzing all rules
    filter_columns = build_filter_columns(ac_rules)

    if not filter_columns:
        return [], []

    # Step 1: Build flat array of (User, Distinct Resource Query Filter, Actions)
    flat_data = build_flat_data(users, filter_columns, ac_rules, filters)

    # Step 2: Transform based on pivot flag
    if pivot:
        return build_pivot_view(users, filter_columns, flat_data, filters)
    else:
        return build_flat_view(flat_data, filters)


def build_flat_data(users, filter_columns, ac_rules, filters):
    """
    Build flat array of (User, Distinct Resource Query Filter, Actions).

    For each user × filter combination:
    - Check if user matches the rule's principals
    - If matched, create an entry with user, filter label, and aggregated actions

    Returns:
        List of dicts with keys: user_id, user_name, filter_label, actions
        Only includes rows where user has access (actions not empty)
    """
    flat_data = []
    action_filter = filters.get("action")

    for user_dict in users:
        user_id = user_dict["name"]
        user_name = user_dict["full_name"]

        for col in filter_columns:
            actions = get_user_actions_for_filter_column(user_id, col, ac_rules)

            # Skip if no actions (user doesn't have access to this filter)
            if not actions:
                continue

            # Apply action filter if specified
            if action_filter:
                action_list = actions.split(", ")
                if action_filter not in action_list:
                    continue
                actions = action_filter  # Show only the filtered action

            flat_data.append(
                {
                    "user_id": user_id,
                    "user_name": user_name,
                    "filter_label": col["label"],
                    "actions": actions,
                }
            )

    return flat_data


def build_flat_view(flat_data, filters):
    """
    Build flat table view with columns: User, Resource Query Filter, Actions.

    Args:
        flat_data: List of dicts with user_id, user_name, filter_label, actions

    Returns:
        Tuple of (columns, data) for flat table view
    """
    columns = [
        {
            "fieldname": "user",
            "label": _("Principal User"),
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "user_id",
            "label": _("User ID"),
            "fieldtype": "Link",
            "options": "User",
            "hidden": 1,
        },
        {
            "fieldname": "filter",
            "label": _("Resource Query Filter"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "actions",
            "label": _("Actions"),
            "fieldtype": "Data",
            "width": 200,
        },
    ]

    data = [
        {
            "user": row["user_name"],
            "user_id": row["user_id"],
            "filter": row["filter_label"],
            "actions": row["actions"],
        }
        for row in flat_data
    ]

    return columns, data


def build_pivot_view(users, filter_columns, flat_data, filters):
    """
    Build pivot (matrix) view with users as rows and filters as columns.

    Args:
        users: List of user dicts
        filter_columns: List of filter column definitions
        flat_data: List of dicts with user_id, user_name, filter_label, actions

    Returns:
        Tuple of (columns, data) for pivot table view
    """
    action_filter = filters.get("action")

    # Create lookup for quick access: {user_id: {filter_label: actions}}
    user_filter_map = {}
    for row in flat_data:
        user_id = row["user_id"]
        filter_label = row["filter_label"]
        actions = row["actions"]

        if user_id not in user_filter_map:
            user_filter_map[user_id] = {}

        user_filter_map[user_id][filter_label] = actions

    # Build columns: User + one column per filter combination
    columns = [
        {
            "fieldname": "user",
            "label": _("Principal User"),
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "user_id",
            "label": _("User ID"),
            "fieldtype": "Link",
            "options": "User",
            "hidden": 1,
        },
    ]

    for col in filter_columns:
        columns.append(
            {
                "fieldname": col["fieldname"],
                "label": col["label"],
                "fieldtype": "Data",
                "width": 200,
            }
        )

    # Build data rows
    data = []
    for user_dict in users:
        user_id = user_dict["name"]
        user_name = user_dict["full_name"]
        row = {"user": user_name, "user_id": user_id}

        # For each filter column, get actions from lookup
        for col in filter_columns:
            actions = user_filter_map.get(user_id, {}).get(col["label"], "")

            # If action filter is specified, show Y/N instead of listing actions
            if action_filter:
                row[col["fieldname"]] = (
                    "Y" if action_filter in actions.split(", ") else "N"
                )
            else:
                row[col["fieldname"]] = actions

        data.append(row)

    return columns, data


def build_filter_columns(ac_rules):
    """
    Build columns based on resource query filters from all rules.

    Process:
    1. List all rules
    2. Expand distinct query filters using get_distinct_resource_query_filters()
       - Each non-exception filter becomes a column
       - Exception filters are combined into the same column (e.g., "Filter1 - ⚠️ Exception1, ⚠️ Exception2")
    3. Group filters by (rule_type, non_exception_filter, exception_filters_tuple)
       - Same filter can appear in multiple columns if used by different rule types (Permit vs Forbid)
    4. For each filter group, aggregate actions from all rules using that combination
       - Actions are stored as a set (deduplicated), then converted to sorted list

    Returns a list of column definitions with:
    - fieldname: unique identifier for the column (e.g., "filter_0", "filter_1")
    - label: display name with emojis (✅ for Permit, 🚫 for Forbid, ⚠️ for exceptions)
    - rules: list of rule info (name, type, actions) that use this filter combination
    - actions: aggregated deduplicated sorted list of actions from all rules using this filter combination

    Columns are sorted alphabetically by their final label before fieldnames are assigned.
    """
    # Dictionary to group filters: key = (rule_type, non_exception_filter, (exception_filters...))
    # Each key represents a unique column
    filter_groups = {}

    # Step 1 & 2: List all rules and expand distinct query filters
    for rule_info in ac_rules:
        rule = frappe.get_doc("AC Rule", rule_info.name)

        # Get distinct resource query filter combinations using the utility
        distinct_filters = rule.get_distinct_resource_query_filters()

        # Skip if no distinct filters
        if not distinct_filters:
            continue

        # Step 3: For each distinct query filter, aggregate actions
        for (
            rule_type,
            non_exception_filter,
            exception_filters_tuple,
        ) in distinct_filters:
            # Create a key for grouping - include rule_type to separate Permit and Forbid rules
            key = (rule_type, non_exception_filter, exception_filters_tuple)

            # Initialize group if not exists
            if key not in filter_groups:
                filter_groups[key] = {
                    "rules": [],
                    "actions": set(),  # Aggregate actions across rules
                }

            # Get actions for this rule
            rule_actions = [action.action for action in rule.actions]

            # Add this rule to the group
            filter_groups[key]["rules"].append(
                {"name": rule.name, "type": rule.type, "actions": rule_actions}
            )

            # Aggregate actions
            filter_groups[key]["actions"].update(rule_actions)

    # Collect all unique filter names to fetch their display names
    all_filter_names = set()
    for key in filter_groups.keys():
        all_filter_names.add(key[1])  # non_exception_filter
        all_filter_names.update(key[2])  # exception_filters_tuple

    # Fetch filter_name (display names) for all query filters
    filter_display_names = {}
    if all_filter_names:
        filter_docs = frappe.get_all(
            "Query Filter",
            filters={"name": ["in", list(all_filter_names)]},
            fields=["name", "filter_name"],
        )
        filter_display_names = {doc.name: doc.filter_name for doc in filter_docs}

    # Build column definitions
    columns = []
    for key, group in filter_groups.items():
        # Extract filter names directly from key - no need to recalculate
        rule_type = key[0]
        non_exception_filter = key[1]
        exception_filters_tuple = key[2]

        # Get display name for non-exception filter
        non_exception_display = filter_display_names.get(
            non_exception_filter, non_exception_filter
        )

        # Build label with filter display names
        if exception_filters_tuple:
            # Add emoji once before all exception filters using display names
            exception_names = sorted(
                [
                    filter_display_names.get(name, name)
                    for name in exception_filters_tuple
                ]
            )
            label = f"{non_exception_display} - ⚠️ {', '.join(exception_names)}"
        else:
            label = non_exception_display

        # Add emoji based on rule type (only for Forbid)
        if rule_type == "Forbid":
            label = f"🚫 {label}"

        columns.append(
            {
                "label": label,
                "rules": group["rules"],
                "actions": sorted(group["actions"]),  # Convert set to sorted list
            }
        )

    # Sort columns by label
    columns.sort(key=lambda col: col["label"])

    # Add fieldname after sorting
    for idx, col in enumerate(columns):
        col["fieldname"] = f"filter_{idx}"

    return columns


def get_user_actions_for_filter_column(user, column, ac_rules):
    """
    Check if a user matches the principals of rules in this resource filter column
    and return aggregated actions.

    For each rule in the column (which all share the same resource filters):
    - Check if the user matches the rule's principals using (M1 OR M2) AND NOT (E1 OR E2) logic
      where M = main principal filters and E = exception principal filters
    - If user matches, add the actions from that rule to the aggregate

    Returns:
        Comma-separated string of sorted action names, or empty string if no matches
    """
    all_actions = set()

    # Check each rule in this column
    for rule_info in column["rules"]:
        # Get the full rule to check its principals
        rule = frappe.get_doc("AC Rule", rule_info["name"])
        principals = rule.resolve_principals()

        # Check if user matches the principals for this rule
        if check_user_matches_rule_principals(user, principals):
            # User matches - add all actions from this rule
            all_actions.update(rule_info["actions"])

    return ", ".join(sorted(all_actions)) if all_actions else ""


def get_users(query_filter_name=None):
    """
    Get list of users with their full names, optionally filtered by a Query Filter.

    Args:
        query_filter_name: Optional name of a Query Filter to restrict which users are shown
                          Must reference User, User Group, Role, or Role Profile doctype

    Returns:
        List of dicts with 'name' (user ID) and 'full_name' fields, sorted by name
        Only enabled users are included
    """

    if query_filter_name:
        # Get users matching the query filter
        query_filter = frappe.get_doc("Query Filter", query_filter_name)

        # Validate that the filter is for User-related doctypes
        if query_filter.reference_doctype not in [
            "User",
            "User Group",
            "Role",
            "Role Profile",
        ]:
            frappe.throw(
                _("Query Filter must reference User, User Group, Role, or Role Profile")
            )

        # Get the SQL from the filter
        filter_sql = get_principal_filter_sql(query_filter)

        if not filter_sql:
            return []

        # Execute the query to get users with full names
        users = frappe.db.sql(
            f"SELECT DISTINCT `name`, `full_name` FROM `tabUser` WHERE {filter_sql} AND enabled = 1 ORDER BY `name`",
            as_dict=True,
        )

        return users
    else:
        # Get all enabled users with full names
        return frappe.db.get_all(
            "User",
            filters={"enabled": 1},
            fields=["name", "full_name"],
            order_by="name",
        )
