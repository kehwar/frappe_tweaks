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
           return {
               "message": f"Item {item.item_code} is below minimum price",
               "data": {
                   "item_code": item.item_code,
                   "rate": item.rate,
                   "min_price": min_price
               }
           }
   return None

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
from frappe.desk.form.assign_to import add as add_assignment
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
        fields=["name", "title", "script", "mandatory"],
    )

    frappe.cache.set_value(cache_key, rules)
    return rules


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
            exec_context = {"doc": doc, "result": None}
            safe_exec(rule["script"], None, exec_context)
            result = exec_context.get("result")

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


def check_mandatory_reviews(doc, method=None):
    """
    Check if document has any mandatory pending reviews and block submission if so.

    Called automatically on before_submit event.

    Args:
            doc: Document instance
            method: Hook method name (unused)

    Raises:
            frappe.ValidationError: If mandatory pending reviews exist
    """

    # Early exit if no rules for this doctype
    rules = get_rules_for_doctype(doc.doctype)
    if not rules:
        return

    # Approve all pending reviews before submission
    submit_all_document_reviews(doc.doctype, doc.name)

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
            _("Cannot submit document with pending mandatory reviews: {0}").format(
                ", ".join(rule_titles)
            ),
            frappe.ValidationError,
        )


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
    # Serialize data for comparison
    review_data_json = (
        frappe.as_json(result.get("data"), indent=0) if result.get("data") else ""
    )

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
        review_doc.review_data = result.get("data")
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
                "review_data": result.get("data"),
                "mandatory": rule["mandatory"],
            }
        )
        review_doc.insert(ignore_permissions=True)
    
    # Assign users to the review (applies to both new and updated reviews)
    _assign_users_to_review(review_doc.name, rule)


def _assign_users_to_review(review_name, rule):
    """
    Assign users to a Document Review based on the rule's user list.
    Follows the Assignment Rules pattern:
    1. List users
    2. If no users, return
    3. Filter by permissions (per-user setting)
    4. Clear existing assignments
    5. Assign users (using array)

    Args:
        review_name: Name of the Document Review document
        rule: Document Review Rule dict with 'name' key
    """
    # Get the full rule document to access the users child table
    rule_doc = frappe.get_doc("Document Review Rule", rule["name"])

    # Step 1 & 2: List users, if no users configured, return
    if not rule_doc.users:
        return

    # Get the review document for permission checks
    review_doc = frappe.get_doc("Document Review", review_name)

    # Step 3: Filter users by permissions (per-user setting)
    users_to_assign = []
    for user_row in rule_doc.users:
        user = user_row.user
        # Check if we should filter by permissions (per-user setting)
        if not user_row.ignore_permissions:
            # Check if user has submit permission on Document Review
            if frappe.has_permission(
                "Document Review", ptype="submit", user=user, doc=review_doc
            ):
                users_to_assign.append(user)
        else:
            # Ignore permissions for this user, assign directly
            users_to_assign.append(user)

    # Step 4: Clear existing assignments on the document
    from frappe.desk.form.assign_to import clear as clear_assignments
    
    try:
        clear_assignments("Document Review", review_name)
    except Exception:
        # If no assignments exist, clear will raise an exception - handle gracefully
        pass

    # Step 5: Assign users (the utility accepts an array)
    if users_to_assign:
        try:
            add_assignment(
                {
                    "doctype": "Document Review",
                    "name": review_name,
                    "assign_to": users_to_assign,  # Pass array of users
                    "description": rule_doc.title,
                }
            )
        except Exception as e:
            # Log but don't fail if assignment fails
            frappe.log_error(
                title=f"Failed to assign Document Review {review_name}",
                message=str(e),
            )


@frappe.whitelist()
def submit_document_review(review_name, review=None, action="approve"):
    """
    Submit a Document Review.
    When submitted, marks the current user's assignment as complete and clears other assignments.

    Args:
        review_name: Name of the Document Review to submit
        review: Optional review comments
        action: Either 'approve' or 'reject'

    Returns:
        dict: Success message
    """
    doc = frappe.get_doc("Document Review", review_name)
    doc.review = review
    
    # Handle assignments: mark current user's task as complete, clear others
    _handle_assignments_on_submit(review_name)
    
    doc.submit()
    if action == "reject":
        doc.cancel()

    return doc


def _handle_assignments_on_submit(review_name):
    """
    Handle assignments when a Document Review is submitted:
    - Mark the current user's assignment as complete
    - Clear all other assignments
    
    Args:
        review_name: Name of the Document Review document
    """
    # Ensure we have a valid user session
    if not frappe.session or not frappe.session.user:
        return
    
    current_user = frappe.session.user
    
    # Get all assignments for this review
    assignments = frappe.get_all(
        "ToDo",
        filters={
            "reference_type": "Document Review",
            "reference_name": review_name,
            "status": "Open",
        },
        fields=["name", "allocated_to"],
    )
    
    if not assignments:
        return
    
    # Separate assignments for bulk operations
    current_user_todos = []
    other_user_todos = []
    
    for assignment in assignments:
        if assignment.allocated_to == current_user:
            current_user_todos.append(assignment.name)
        else:
            other_user_todos.append(assignment.name)
    
    # Bulk update current user's assignments to Closed
    if current_user_todos:
        frappe.db.set_value("ToDo", {"name": ["in", current_user_todos]}, "status", "Closed")
    
    # Bulk delete other users' assignments
    if other_user_todos:
        for todo_name in other_user_todos:
            frappe.delete_doc("ToDo", todo_name, ignore_permissions=True)


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
