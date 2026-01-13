# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

"""
Workflow integration with AC Rules system.

This module provides handlers for workflow-related hooks that integrate
AC Rules permission checking with Frappe's workflow system.
"""

import frappe
from frappe import _


def check_workflow_transition_permission(doc, method=None, transition=None):
    """
    Doc event handler for before_transition.
    Checks AC Rules if the workflow action is managed.
    Raises exception to block transition if permission denied.

    Args:
        doc: Document being transitioned
        method: Method name (before_transition)
        transition: Transition object with action, state, next_state, etc.
    """
    if not transition:
        return

    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access

    user = frappe.session.user

    # Check if AC Rules manage this workflow action
    result = has_resource_access(
        doctype=doc.doctype,
        action=transition.action,  # e.g., "Approve", "Submit"
        user=user,
    )

    if not result.get("unmanaged"):
        # AC Rules are managing this workflow action
        if not result.get("access"):
            frappe.throw(
                _("You do not have permission to perform this workflow action"),
                frappe.PermissionError,
            )

    # If unmanaged or has access, do nothing (let transition proceed)


def filter_transitions_by_ac_rules(doc, transitions, workflow):
    """
    Hook handler for filter_workflow_transitions.
    Filters out transitions the user doesn't have permission for via AC Rules.

    Args:
        doc: Document object
        transitions: List of transition objects
        workflow: Workflow object

    Returns:
        Filtered list of transitions
    """
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access

    user = frappe.session.user
    filtered_transitions = []

    for transition in transitions:
        # Check if AC Rules manage this workflow action
        result = has_resource_access(
            doctype=doc.doctype, action=transition.action, user=user
        )

        if not result.get("unmanaged"):
            # Managed by AC Rules - check permission
            if result.get("access"):
                filtered_transitions.append(transition)
            # If no access, skip this transition
        else:
            # Unmanaged by AC Rules - include it
            filtered_transitions.append(transition)

    return filtered_transitions


def get_workflow_action_permission_query_conditions(user=None, doctype=None):
    """
    Additional permission query conditions for Workflow Action doctype.

    Adds AC Rules filtering on top of Frappe's role-based filtering.
    Frappe automatically combines this with the original conditions using AND.

    Strategy:
    1. Get all (doctype, state, action) triples from open workflow actions
    2. For each (doctype, action), get AC Rules filter as SELECT query
    3. Group by (doctype, state) and OR all action queries together
    4. Build final condition checking if reference_name is in any allowed action query

    Args:
        user: User to check (defaults to session user)
        doctype: DocType name (should be "Workflow Action")

    Returns:
        str: SQL WHERE clause for AC Rules filtering, or "" if no filtering needed
    """
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import get_resource_filter_query

    if not user:
        user = frappe.session.user

    if user == "Administrator":
        return ""

    # Get all distinct (reference_doctype, workflow_state, action) triples
    doctype_state_action_triples = frappe.db.sql(
        """
        SELECT DISTINCT 
            wa.reference_doctype,
            wa.workflow_state,
            wt.action
        FROM `tabWorkflow Action` wa
        INNER JOIN `tabWorkflow` w 
            ON w.document_type = wa.reference_doctype
        INNER JOIN `tabWorkflow Transition` wt
            ON wt.parent = w.name 
            AND wt.state = wa.workflow_state
        WHERE wa.status = 'Open'
    """,
        as_dict=True,
    )

    if not doctype_state_action_triples:
        return ""

    # Group triples by (doctype, state)
    # Structure: {(doctype, state): [action1, action2, ...]}
    grouped = {}
    for triple in doctype_state_action_triples:
        key = (triple.reference_doctype, triple.workflow_state)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(triple.action)

    # Build conditions for each (doctype, state) group
    conditions = []

    for (reference_doctype, workflow_state), actions in grouped.items():
        # Get AC Rules filter for each action
        action_queries = []
        has_total_access = False  # Track if any action has unmanaged or total access

        for action in actions:
            action_scrubbed = frappe.scrub(action)

            # Get filter query from AC Rules
            result = get_resource_filter_query(
                doctype=reference_doctype,
                action=action_scrubbed,
                user=user,
                debug=False,
            )

            if result.get("unmanaged") or result.get("access") == "total":
                # Not managed by AC Rules OR user has total access
                # Either way, AC Rules doesn't restrict this doctype/state
                # No need to add any conditions for this doctype/state
                has_total_access = True
                break  # Short-circuit: no need to check other actions
            elif result.get("access") == "none":
                # User has no access for this action via AC Rules
                # Don't add query (implicitly blocks this action)
                pass
            elif result.get("access") == "partial":
                # User has conditional access
                filter_query = result.get("query", "")
                if filter_query:
                    # Build SELECT query that returns allowed document names
                    select_query = f"""
                        SELECT name 
                        FROM `tab{reference_doctype}` 
                        WHERE {filter_query}
                    """
                    action_queries.append(
                        f"`tabWorkflow Action`.`reference_name` IN ({select_query})"
                    )

        # If any action has total access, skip this doctype/state (no AC Rules restrictions)
        if has_total_access:
            continue

        # If no action queries, all actions must have access=none (all blocked by AC Rules)
        if not action_queries:
            # Block workflow actions for this doctype/state entirely
            conditions.append(
                f"""
                NOT (
                    `tabWorkflow Action`.`reference_doctype` = {frappe.db.escape(reference_doctype)}
                    AND `tabWorkflow Action`.`workflow_state` = {frappe.db.escape(workflow_state)}
                )
            """
            )
        else:
            # Combine action queries with OR
            # Show workflow action if it's this doctype/state AND reference_name matches at least one allowed action
            combined_action_queries = " OR ".join([f"({q})" for q in action_queries])
            conditions.append(
                f"""
                (
                    `tabWorkflow Action`.`reference_doctype` = {frappe.db.escape(reference_doctype)}
                    AND `tabWorkflow Action`.`workflow_state` = {frappe.db.escape(workflow_state)}
                    AND ({combined_action_queries})
                )
            """
            )

    if not conditions:
        return ""

    # Combine all conditions with OR (each condition handles a different doctype/state)
    return " OR ".join([f"({c})" for c in conditions])


def has_workflow_action_permission_via_ac_rules(user, transition, doc):
    """
    Check if a user has AC Rules permission for a specific workflow action.

    Args:
        user: User ID to check permission for
        transition: Workflow transition dict with 'action', 'allowed', etc.
        doc: Document being actioned

    Returns:
        bool: True if user has permission (or action is unmanaged), False otherwise
    """
    from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import has_resource_access

    action = transition.get("action")
    if not action:
        return True  # No action specified, allow by default

    action_scrubbed = frappe.scrub(action)

    # Check if user has AC Rules access to this action
    result = has_resource_access(doctype=doc.doctype, action=action_scrubbed, user=user)

    if result.get("unmanaged"):
        # Not managed by AC Rules, user already passed role check
        return True

    # Return AC Rules access result
    return bool(result.get("access"))
