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

        if review.docstatus == 0:
            # Add submit button for pending reviews
            content += f"""
                <div style="margin-top: 10px;">
                    <button class="btn btn-xs btn-primary" 
                        onclick="frappe.call({{
                            method: 'frappe.client.submit',
                            args: {{
                                doc: {{
                                    doctype: 'Document Review',
                                    name: '{review.name}'
                                }}
                            }},
                            callback: function(r) {{
                                if (!r.exc) {{
                                    cur_frm.reload_doc();
                                }}
                            }}
                        }}); return false;">
                        <svg class="icon icon-sm" style=""><use href="#icon-check"></use></svg>
                        {_("Approve")}
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
