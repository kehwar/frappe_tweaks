from typing import Union

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model import workflow
from frappe.model.docstatus import DocStatus
from frappe.model.document import Document
from frappe.model.workflow import (
    WorkflowStateError,
    WorkflowTransitionError,
    get_workflow,
    get_workflow_name,
    has_approval_access,
    is_transition_condition_satisfied,
)
from frappe.utils import cint
from frappe.workflow.doctype.workflow.workflow import Workflow


def on_change(doc, method=None):
    # Get the workflow linked to the document type
    workflow_name = get_workflow_name(doc.doctype)
    if workflow_name:
        apply_auto_workflow_transition(doc)


def create_workflow_fields():

    create_custom_fields(
        {
            "Workflow Transition": [
                {
                    "fieldname": "auto_apply",
                    "fieldtype": "Check",
                    "label": "Auto Apply",
                    "insert_after": "allow_self_approval",
                }
            ]
        },
        ignore_validate=True,
    )


workflow_script_hooks = {
    "doc_events": {"*": {"on_change": ["tweaks.custom.doctype.workflow.on_change"]}},
    "after_install": ["tweaks.custom.doctype.workflow.create_workflow_fields"],
}


@frappe.whitelist()
def get_transitions(
    doc: Union["Document", str, dict],
    workflow: "Workflow" = None,
    raise_exception: bool = False,
    user=None,
) -> list[dict]:
    """Return list of possible transitions for the given doc"""
    from frappe.model.document import Document

    if not isinstance(doc, Document):
        doc = frappe.get_doc(frappe.parse_json(doc))
        doc.load_from_db()

    if doc.is_new():
        return []

    workflow = workflow or get_workflow(doc.doctype)
    current_state = doc.get(workflow.workflow_state_field)

    if not current_state:
        if raise_exception:
            raise WorkflowStateError
        else:
            frappe.throw(_("Workflow State not set"), WorkflowStateError)

    transitions = []
    roles = frappe.get_roles()

    for transition in workflow.transitions:
        if transition.state == current_state and transition.allowed in roles:
            if not is_transition_condition_satisfied(transition, doc):
                continue
            transitions.append(transition.as_dict())

    return transitions


@frappe.whitelist()
def apply_workflow(doc, action, update=True, workflow=None, user=None):
    """
    Perform a workflow action on the current document.

    Args:
        doc: The document to which the workflow action is applied.
        action: The intended workflow action.
        update: Whether to update the document after applying the workflow.
        workflow: Workflow object (optional).
        user: The user context for the workflow.

    Returns:
        Updated document after applying the workflow action.
    """
    # Prepare the document and workflow context
    doc = get_doc(doc)
    workflow = workflow or get_workflow(doc.doctype)
    user = user or frappe.session.user
    transitions = get_transitions(doc, workflow, user=user)

    # Find the transition matching the given action
    transition = None
    for t in transitions:
        if t.action == action:
            transition = t

    # Throw error if transition is not found
    if not transition:
        frappe.throw(_("Not a valid Workflow Action"), WorkflowTransitionError)

    return apply_workflow_transition(
        doc, transition, update=update, workflow=workflow, user=user
    )


def apply_workflow_transition(doc, transition, update=True, workflow=None, user=None):
    """
    Execute a transition as part of the document's workflow.

    Args:
        doc: The document on which to apply the workflow transition.
        transition: The transition to apply.
        update: Whether to save the document after transition.
        workflow: Workflow object (optional).
        user: The user context for the workflow.

    Returns:
        Updated document after applying the workflow transition.
    """
    # Prepare the document and workflow context
    doc = get_doc(doc)
    workflow = workflow or get_workflow(doc.doctype)
    user = user or frappe.session.user

    # Check if user has permission for the transition
    if not has_approval_access(user, doc, transition):
        frappe.throw(_("Self approval is not allowed"))

    # Update workflow state field in the document
    starting_state = doc.get(workflow.workflow_state_field)
    if not doc.get(f"{workflow.workflow_state_field}_starting"):
        doc.set(f"{workflow.workflow_state_field}_starting", starting_state)
    doc.set(workflow.workflow_state_field, transition.next_state)

    # Get settings for the next state and update fields accordingly
    next_state = next(d for d in workflow.states if d.state == transition.next_state)
    if next_state.update_field:
        doc.set(next_state.update_field, next_state.update_value)

    # Update document status based on the workflow's next state
    new_docstatus = cint(next_state.doc_status)
    if doc.docstatus.is_draft() and new_docstatus == DocStatus.draft():
        doc.docstatus = new_docstatus
    elif doc.docstatus.is_draft() and new_docstatus == DocStatus.submitted():
        doc.docstatus = new_docstatus
    elif doc.docstatus.is_submitted() and new_docstatus == DocStatus.submitted():
        doc.docstatus = new_docstatus
    elif doc.docstatus.is_submitted() and new_docstatus == DocStatus.cancelled():
        doc.docstatus = new_docstatus
    else:
        frappe.throw(_("Illegal Document Status for {0}").format(next_state.state))

    # Save document changes and apply scripts based on events
    if update:

        doc.run_method("before_transition", transition)

        doc.save(ignore_permissions=True)
        if starting_state == doc.get(f"{workflow.workflow_state_field}_starting"):
            doc.add_comment("Workflow", _(doc.get(workflow.workflow_state_field)))

        doc.run_method("after_transition", transition)

    return doc


def apply_auto_workflow_transition(doc, update=True, workflow=None, user=None):
    """
    Automatically apply the highest priority workflow transition that is set to auto-apply.

    Args:
        doc: The document to which the workflow is applied.
        update: Whether to update the document after transition.
        workflow: Workflow object (optional).
        user: The user context for the workflow.

    Returns:
        Updated document if an auto transition is applied; else, the original document.
    """
    # Prepare the document and workflow context
    doc = get_doc(doc)
    workflow = workflow or get_workflow(doc.doctype)
    user = user or frappe.session.user

    transitions = get_transitions(doc, workflow, user=user)
    for t in transitions:
        if t.auto_apply == 1:
            return apply_workflow_transition(
                doc, t, update=update, workflow=workflow, user=user
            )

    return doc


def get_doc(doc):
    """
    Retrieve or convert the given input into a Document object from the database.

    Args:
        doc: The documentation or JSON-like structure to transform.

    Returns:
        Document instance fetched from the database.
    """
    # Convert input to Document, if necessary, and retrieve from database
    if not isinstance(doc, Document):
        doc = frappe.get_doc(frappe.parse_json(doc))
        doc.load_from_db()
    return doc


def apply_workflow_patches():
    # refactor: Migrate to frappe/model/workflow.py
    # - Replace get_transitions and apply_workflow with enhanced versions above
    # - Add apply_workflow_transition and apply_auto_workflow_transition functions
    # - Add support for before_transition and after_transition document methods
    workflow.get_transitions = get_transitions
    workflow.apply_workflow = apply_workflow
