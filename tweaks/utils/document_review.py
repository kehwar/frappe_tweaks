# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

"""
Document Review System

This module provides a flexible document review/approval system where:
- Document Review Rules define validation checks via Python scripts
- Document Reviews track approval state as submittable records
- Rules are evaluated automatically on document changes
- Mandatory reviews block document submission

Usage Examples:

1. Workflow Transition Condition (check if reviews are cleared):
   frappe.db.count("Document Review", {
       "reference_doctype": doc.doctype,
       "reference_name": doc.name,
       "docstatus": 0
   }) == 0

2. Script Example (Document Review Rule):
   # Check if any item is below minimum price
   for item in doc.items:
       min_price = frappe.db.get_value("Item Price", {
           "item_code": item.item_code,
           "price_list": doc.selling_price_list
       }, "min_price")

       if min_price and item.rate < min_price:
           # Option 1: Set result variable (traditional approach)
           result = {
               "message": f"Item {item.item_code} is below minimum price",
               "data": {
                   "item_code": item.item_code,
                   "rate": item.rate,
                   "min_price": min_price
               }
           }
           # Option 2: Set message and data variables directly (new approach)
           # message = f"Item {item.item_code} is below minimum price"
           # data = {
           #     "item_code": item.item_code,
           #     "rate": item.rate,
           #     "min_price": min_price
           # }
           break

3. Form Banner Custom Script:
   frappe.call({
       method: "frappe.client.get_count",
       args: {
           doctype: "Document Review",
           filters: {
               reference_doctype: frm.doctype,
               reference_name: frm.docname,
               docstatus: 0
           }
       },
       callback: (r) => {
           if (r.message > 0) {
               frm.dashboard.add_indicator(
                   __("Pending Reviews: {0}", [r.message]),
                   "orange"
               );
           }
       }
   });
"""

import json

import frappe
from frappe import _
from frappe.utils.safe_exec import safe_exec


def get_rules_for_doctype(doctype):
    """
    Get all active Document Review Rules for a doctype.
    Results are cached per doctype.

    Args:
            doctype: DocType name

    Returns:
            List of Document Review Rule documents
    """

    # Skip during migration
    if frappe.flags.in_migrate or frappe.flags.in_install:
        return

    cache_key = f"document_review_rules:{doctype}"
    cached_rules = frappe.cache.get_value(cache_key)

    if cached_rules is not None:
        return cached_rules

    rules = frappe.get_all(
        "Document Review Rule",
        filters={"reference_doctype": doctype, "disabled": 0},
        fields=[
            "name",
            "title",
            "script",
            "mandatory",
            "assign_condition",
            "unassign_condition",
            "submit_condition",
            "validate_condition",
        ],
    )

    frappe.cache.set_value(cache_key, rules)
    return rules


def evaluate_condition(condition_script, doc):
    """
    Evaluate a condition script with the document context.
    
    Args:
        condition_script: Python code to evaluate
        doc: Document instance
        
    Returns:
        bool: True if condition is met, False otherwise
    """
    if not condition_script:
        return False
    
    try:
        exec_context = {"doc": doc, "result": None}
        safe_exec(condition_script, None, exec_context)
        result = exec_context.get("result")
        return bool(result)
    except Exception as e:
        frappe.log_error(
            title=f"Error evaluating condition for {doc.doctype} {doc.name}",
            message=f"Condition script: {condition_script}\nError: {str(e)}"
        )
        return False


def evaluate_document_reviews(doc, method=None):
    """
    Evaluate all Document Review Rules for a document and create/update/delete
    Document Review records based on rule results.

    Called automatically on document on_change event.

    Args:
            doc: Document instance
            method: Hook method name (unused)
    """
    # Early exit if no rules for this doctype
    rules = get_rules_for_doctype(doc.doctype)
    if not rules:
        return
    
    # Evaluate each rule
    for rule in rules:
        try:
            # Execute rule script
            exec_context = {"doc": doc, "result": None, "message": None, "data": None}
            safe_exec(rule["script"], None, exec_context)
            result = exec_context.get("result")
            
            # Support direct message and data variables as an alternative to result dict
            if result is None:
                message = exec_context.get("message")
                data = exec_context.get("data")
                
                # If message is set directly, construct result dict
                if message is not None:
                    result = {
                        "message": message,
                        "data": data
                    }

            if result is None:
                # No review needed - delete any draft reviews for this rule
                _delete_draft_reviews(doc.doctype, doc.name, rule["name"])
            else:
                # Review needed - create or update draft review
                _create_or_update_review(doc, rule, result)

        except Exception as e:
            frappe.throw(
                _("Error evaluating Document Review Rule '{0}': {1}").format(
                    rule["title"], str(e)
                )
            )
    
    # After all rules are evaluated, check conditions for actions
    # Always check conditions, not just when reviews are created
    _evaluate_rule_conditions(doc, rules)


def check_mandatory_reviews(doc, method=None):
    """
    DEPRECATED: This function is kept for backward compatibility but is now a no-op.
    
    The document review system now uses condition-based evaluation instead of hooks.
    Use validate_condition in Document Review Rule to control when validation occurs.
    
    Called automatically on before_submit event (legacy hook).

    Args:
            doc: Document instance
            method: Hook method name (unused)
    """
    # No-op: Validation is now handled by validate_condition in rules
    pass


def _delete_draft_reviews(reference_doctype, reference_name, review_rule):
    """
    Delete all draft Document Review records for a specific rule and document.

    Args:
            reference_doctype: Reference document type
            reference_name: Reference document name
            review_rule: Document Review Rule name
    """
    draft_reviews = frappe.get_all(
        "Document Review",
        filters={
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "review_rule": review_rule,
            "docstatus": 0,
        },
        pluck="name",
    )

    for review_name in draft_reviews:
        frappe.delete_doc("Document Review", review_name, ignore_permissions=True)


def _create_or_update_review(doc, rule, result):
    """
    Create or update a Document Review based on rule evaluation result.

    Args:
            doc: Source document instance
            rule: Document Review Rule dict
            result: Script result dict with 'message' and 'data' keys
    """
    # Serialize data for storage and comparison
    review_data = result.get("data")
    review_data_json = (
        frappe.as_json(review_data, indent=0) if review_data else ""
    )
    review_data_for_storage = review_data_json if review_data else None

    # Check if a submitted review exists with the same data
    submitted_reviews = frappe.get_all(
        "Document Review",
        {
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "review_rule": rule["name"],
            "docstatus": 1,
        },
        ["name", "review_data"],
    )

    # If submitted review exists with same data, no action needed
    for submitted_review in submitted_reviews:
        submitted_data_json = (
            frappe.as_json(json.loads(submitted_review.get("review_data")), indent=0)
            if submitted_review.get("review_data")
            else ""
        )
        if submitted_data_json == review_data_json:
            _delete_draft_reviews(doc.doctype, doc.name, rule["name"])
            return

    # Check if draft review exists
    existing_draft = frappe.db.get_value(
        "Document Review",
        {
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "review_rule": rule["name"],
            "docstatus": 0,
        },
        "name",
    )

    if existing_draft:
        # Update existing draft
        review_doc = frappe.get_doc("Document Review", existing_draft)
        review_doc.message = result.get("message", "")
        review_doc.review_data = review_data_for_storage
        review_doc.mandatory = rule["mandatory"]
        review_doc.save(ignore_permissions=True)
    else:
        # Create new draft review
        review_doc = frappe.get_doc(
            {
                "doctype": "Document Review",
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "review_rule": rule["name"],
                "message": result.get("message", ""),
                "review_data": review_data_for_storage,
                "mandatory": rule["mandatory"],
            }
        )
        review_doc.insert(ignore_permissions=True)
    
    # NOTE: Auto-assignments are now handled by condition evaluation, not here


def _evaluate_rule_conditions(doc, rules):
    """
    Evaluate condition scripts for all rules and execute appropriate actions.
    
    Args:
        doc: Reference document instance
        rules: List of Document Review Rule dicts
    """
    # Track which conditions are true across all rules
    should_assign = False
    should_unassign = False
    should_submit = False
    should_validate = False
    
    # Evaluate each rule's conditions
    for rule in rules:
        if evaluate_condition(rule.get("assign_condition"), doc):
            should_assign = True
        
        if evaluate_condition(rule.get("unassign_condition"), doc):
            should_unassign = True
        
        if evaluate_condition(rule.get("submit_condition"), doc):
            should_submit = True
        
        if evaluate_condition(rule.get("validate_condition"), doc):
            should_validate = True
    
    # Execute actions based on evaluated conditions
    # Order matters: unassign before assign, submit before validate
    
    if should_unassign:
        _clear_all_assignments(doc.doctype, doc.name)
    
    if should_assign:
        apply_auto_assignments(doc.doctype, doc.name)
    
    if should_submit:
        # Auto-submit all pending reviews that the current user can submit
        submit_all_document_reviews(doc.doctype, doc.name)
    
    if should_validate:
        # Check for mandatory pending reviews and throw error if found
        _validate_no_pending_mandatory_reviews(doc)


def _clear_all_assignments(ref_doctype, ref_name):
    """
    Clear all open assignments for a referenced document.
    
    Args:
        ref_doctype: The doctype of the referenced document
        ref_name: The name of the referenced document
    """
    from frappe.desk.form.assign_to import set_status
    
    # Get all open/pending assignments for the referenced document
    current_assignments = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": ref_doctype,
            "reference_name": ref_name,
            "status": ("not in", ("Cancelled", "Closed")),
        },
        fields=["name", "allocated_to"],
    )
    
    # Cancel all open assignments
    for assignment in current_assignments:
        try:
            set_status(
                ref_doctype,
                ref_name,
                todo=assignment["name"],
                assign_to=assignment["allocated_to"],
                status="Cancelled",
                ignore_permissions=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"Failed to clear assignment for {assignment['allocated_to']}",
                message=str(e),
            )


def _validate_no_pending_mandatory_reviews(doc):
    """
    Check if document has any mandatory pending reviews and throw error if so.
    
    Args:
        doc: Document instance
        
    Raises:
        frappe.ValidationError: If mandatory pending reviews exist
    """
    # Check for mandatory pending reviews
    pending_mandatory = frappe.get_all(
        "Document Review",
        filters={
            "reference_doctype": doc.doctype,
            "reference_name": doc.name,
            "docstatus": 0,
            "mandatory": 1,
        },
        fields=["review_rule"],
        pluck="review_rule",
    )

    if pending_mandatory:
        # Get rule titles for error message
        rule_titles = frappe.get_all(
            "Document Review Rule",
            filters={"name": ["in", pending_mandatory]},
            pluck="title",
        )

        frappe.throw(
            _("Cannot proceed with pending mandatory reviews: {0}").format(
                ", ".join(rule_titles)
            ),
            frappe.ValidationError,
        )


def apply_auto_assignments(ref_doctype, ref_name):
    """
    Apply auto-assignments to a referenced document based on ALL pending document reviews.
    
    This function implements differential assignment logic to prevent notification spam:
    - Queries all pending (draft) document reviews for the referenced document
    - Calculates the union of users from all review rules with per-user permission filtering
    - Compares desired users with current assignments to determine changes
    - Only creates assignments for NEW users (sends notifications)
    - Leaves EXISTING users unchanged (no notifications)
    - Cancels assignments for REMOVED users
    - Uses review message as personalized todo description for new assignments
    
    Args:
        ref_doctype: The doctype of the referenced document (e.g., "Sales Order")
        ref_name: The name of the referenced document
    
    Permission Filtering (per-user):
        - When ignore_permissions=False: User must have submit permission on Document Review 
          AND read permission on the referenced document
        - When ignore_permissions=True: User is assigned regardless of permissions
    
    Example:
        # Called automatically when conditions are met
        apply_auto_assignments("Sales Order", "SO-001")
    """
    from frappe.desk.form.assign_to import add as add_assignment, set_status
    
    # Get the referenced document for permission checks
    try:
        ref_doc = frappe.get_doc(ref_doctype, ref_name)
    except frappe.DoesNotExistError:
        # Referenced document doesn't exist, cannot assign
        return
    
    # Get all pending (draft) document reviews for this reference document
    pending_reviews = frappe.get_all(
        "Document Review",
        filters={
            "reference_doctype": ref_doctype,
            "reference_name": ref_name,
            "docstatus": 0,  # Draft only
        },
        fields=["name", "review_rule", "message"],
    )
    
    # Collect users from all pending reviews and track their review messages
    desired_users = set()
    user_messages = {}  # Maps user to review message (one per user)
    
    if pending_reviews:
        for review in pending_reviews:
            # Get the review rule to access user configuration
            rule = frappe.get_doc("Document Review Rule", review.review_rule)
            
            if not rule.users:
                continue
            
            # Get the review document for permission checks
            review_doc = frappe.get_doc("Document Review", review.name)
            
            # Filter users by permissions (per-user setting)
            for user_row in rule.users:
                user = user_row.user
                
                # Check if we should filter by permissions (per-user setting)
                if not user_row.ignore_permissions:
                    try:
                        # Check if user has submit permission on Document Review AND read permission on referenced doc
                        has_review_permission = frappe.has_permission(
                            "Document Review", ptype="submit", user=user, doc=review_doc
                        )
                        has_ref_permission = frappe.has_permission(
                            ref_doctype, ptype="read", user=user, doc=ref_doc
                        )
                        if has_review_permission and has_ref_permission:
                            desired_users.add(user)
                            # Store the message for this user (only if not already set)
                            if user not in user_messages and review.message:
                                user_messages[user] = review.message
                    except Exception:
                        # Permission check failed, skip this user
                        continue
                else:
                    # Ignore permissions for this user, assign directly
                    desired_users.add(user)
                    # Store the message for this user (only if not already set)
                    if user not in user_messages and review.message:
                        user_messages[user] = review.message
    
    # Get current assignments for the referenced document
    current_assignments = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": ref_doctype,
            "reference_name": ref_name,
            "status": ("not in", ("Cancelled", "Closed")),
        },
        fields=["name", "allocated_to"],
    )
    
    # Build a set of currently assigned users
    current_users = {a["allocated_to"] for a in current_assignments}
    
    # Build a dict mapping users to their assignment names
    user_to_assignment = {a["allocated_to"]: a["name"] for a in current_assignments}
    
    # Calculate differences
    new_users = desired_users - current_users  # Users to add
    removed_users = current_users - desired_users  # Users to remove
    # existing_users = desired_users & current_users  # Users that remain (no action needed)
    
    # Handle removed users - cancel all assignments
    for user in removed_users:
        assignment_name = user_to_assignment[user]
        
        try:
            set_status(
                ref_doctype,
                ref_name,
                todo=assignment_name,
                assign_to=user,
                status="Cancelled",
                ignore_permissions=True,
            )
        except Exception as e:
            frappe.log_error(
                title=f"Failed to update assignment status for {user}",
                message=str(e),
            )
    
    # Handle new users - create assignments with personalized descriptions
    if new_users:
        for user in new_users:
            # Get the message for this user, fallback to generic message
            description = user_messages.get(user, "Document Review")
            
            try:
                add_assignment(
                    {
                        "doctype": ref_doctype,
                        "name": ref_name,
                        "assign_to": [user],  # Assign one user at a time to use custom description
                        "description": description,
                    }
                )
            except Exception as e:
                # Log assignment failure but don't break the review creation
                frappe.log_error(
                    title=f"Failed to assign user {user} for {ref_doctype} {ref_name}",
                    message=str(e),
                )


@frappe.whitelist()
def submit_document_review(review_name, review=None, action="approve"):
    """
    Submit a Document Review.

    Args:
        review_name: Name of the Document Review to submit
        review: Optional review comments
        action: Either 'approve' or 'reject'

    Returns:
        dict: Success message
    """
    doc = frappe.get_doc("Document Review", review_name)
    doc.review = review
    doc.submit()
    if action == "reject":
        doc.cancel()

    return doc


@frappe.whitelist()
def submit_all_document_reviews(doctype, docname, review=None, action="approve"):
    """
    Submit all Document Reviews for a document.

    Args:
        doctype: Reference document type
        docname: Reference document name
        review: Optional review comments (applied to all reviews)
        action: Either 'approve' or 'reject'

    Returns:
        dict: Summary of results
    """
    # Get all draft document reviews for this document
    reviews = frappe.get_list(
        "Document Review",
        filters={
            "reference_doctype": doctype,
            "reference_name": docname,
            "docstatus": 0,
        },
        pluck="name",
    )

    results = {"total": len(reviews), "successful": 0, "failed": 0, "errors": []}

    for review_name in reviews:
        try:
            submit_document_review(review_name, review, action)
            results["successful"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"review": review_name, "error": str(e)})

    return results


@frappe.whitelist()
def get_document_review_status(doctype, docname):
    """
    Get the review status for a document.

    Args:
        doctype: Reference document type
        docname: Reference document name

    Returns:
        str: One of:
            - "Approved": No pending reviews
            - "Pending Review": Has pending reviews but user cannot approve any
            - "Can Approve": User can approve some pending reviews
            - "Can Submit": User can approve all pending reviews
    """
    filters = {
        "reference_doctype": doctype,
        "reference_name": docname,
        "docstatus": 0,
    }

    # Get all pending reviews
    all_pending = frappe.get_list(
        "Document Review",
        filters=filters,
        pluck="name",
    )

    if not all_pending:
        return "Approved"

    # Check which reviews user can approve
    can_approve = [
        review_name
        for review_name in all_pending
        if frappe.has_permission("Document Review", doc=review_name, ptype="submit")
    ]

    if not can_approve:
        return "Pending Review"
    elif len(can_approve) == len(all_pending):
        return "Can Submit"
    else:
        return "Can Approve"


def add_document_review_bootinfo(bootinfo):
    """
    Add Document Review related data to bootinfo.

    Args:
        bootinfo: Dict to add data to
    """
    bootinfo["doctypes_with_document_review_rules"] = frappe.get_all(
        "Document Review Rule",
        filters={"disabled": 0},
        pluck="reference_doctype",
        distinct=True,
    )


def get_document_reviews_for_timeline(doctype, docname):
    """
    Get Document Reviews for a document to display in the timeline.

    This function is called via the additional_timeline_content hook.

    Args:
            doctype: Reference document type
            docname: Reference document name

    Returns:
            List of Document Review dicts for timeline display
    """
    frappe.has_permission(doctype, doc=docname, ptype="read", throw=True)

    reviews = frappe.get_all(
        "Document Review",
        filters={
            "reference_doctype": doctype,
            "reference_name": docname,
        },
        fields=[
            "name",
            "creation",
            "modified",
            "owner",
            "modified_by",
            "docstatus",
            "review_rule",
            "message",
            "mandatory",
        ],
        order_by="creation desc",
    )

    timeline_contents = []
    for review in reviews:
        # Build status for indicator pill
        if review.docstatus == 0:
            doc_status = _("Pending Review")
            status_indicator = "orange"
        elif review.docstatus == 1:
            doc_status = _("Approved")
            status_indicator = "green"
        else:
            doc_status = _("Rejected")
            status_indicator = "grey"

        # Build content with submit button for draft reviews
        content = frappe.utils.markdown(review.message) if review.message else ""

        if review.docstatus == 0 and frappe.has_permission(
            "Document Review", doc=review.name, ptype="submit"
        ):

            # Add submit button for pending reviews
            content += f"""
                <div style="margin-top: 10px;">
                    <button class="btn btn-xs btn-primary document-review-approve-btn" 
                        onclick="cur_frm.trigger('document_review_approve', '{review.name}'); return false;">
                        {_("Review")}
                    </button>
                </div>
            """

        # Prepare template data for timeline_message_box
        # Template expects { doc: {...} } context
        template_data = {
            "doc": {
                "owner": review.modified_by,
                "creation": review.creation,
                "content": content,
                "_url": frappe.utils.get_url_to_form("Document Review", review.name),
                "_doc_status": doc_status,
                "_doc_status_indicator": status_indicator,
                "type": "Document Review",
                "review_docstatus": review.docstatus,
                "communication_type": f"Document Review::{review.docstatus}",
            }
        }

        timeline_contents.append(
            {
                "icon": "milestone",
                "is_card": True,
                "creation": review.modified,
                "template": "timeline_message_box",
                "template_data": template_data,
            }
        )

    return timeline_contents


def get_document_review_permission_query_conditions(user=None, doctype=None):
    """
    Permission query conditions for Document Review doctype.

    Users can only see Document Reviews for documents they have read permission on.

    Args:
        user: User to check (defaults to session user)
        doctype: DocType name (should be "Document Review")

    Returns:
        str: SQL WHERE conditions to filter Document Reviews
    """
    if not user:
        user = frappe.session.user

    # Administrator can see all reviews
    if user == "Administrator":
        return ""

    # Get all doctypes that have Document Reviews
    doctypes_with_reviews = frappe.get_all(
        "Document Review",
        pluck="reference_doctype",
        distinct=True,
    )

    if not doctypes_with_reviews:
        # No rules means no reviews
        return "1=0"

    # Build conditions for each doctype
    conditions = []
    for dt in doctypes_with_reviews:
        try:
            # Get the query that includes permission filtering
            query = frappe.db.get_list(
                dt,
                fields=["name"],
                run=0,
                order_by=None,
            )

            # Build condition: reference_doctype = 'X' AND reference_name IN (query)
            condition = f"(`tabDocument Review`.reference_doctype = {frappe.db.escape(dt)} AND `tabDocument Review`.reference_name IN ({query}))"
            conditions.append(condition)
        except Exception:
            # Skip doctypes that fail (might not exist, no permission, etc.)
            continue

    if not conditions:
        # No accessible doctypes means no reviews visible
        return "1=0"

    # OR all conditions together
    return f"({' OR '.join(conditions)})"
