# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

from typing import Union

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.db_query import DatabaseQuery
from frappe.model.docstatus import DocStatus
from frappe.model.document import Document
from frappe.model.workflow import (
    WorkflowStateError,
    WorkflowTransitionError,
    get_workflow,
    get_workflow_name,
    has_approval_access,
)
from frappe.permissions import _pop_debug_log
from frappe.utils import cint, safe_exec
from frappe.workflow.doctype.workflow.workflow import Workflow


class EventScript(Document):

    def before_validate(self):

        self.priority = self.priority or 100

        for parameter in self.parameters:
            parameter.before_validate()

        self.doctype_filter = self.document_type or self.document_type_group

        self.user_filter = ",".join(
            [
                filter
                for filter in [self.user, self.user_group, self.role, self.role_profile]
                if filter
            ]
        )

        if self.doctype_event not in [
            "before_transition",
            "after_transition",
            "transition_condition",
        ]:
            self.workflow_action = None

        if self.doctype_event not in [
            "has_permission",
            "has_field_permission",
        ]:
            self.action = None

    def validate(self):

        if not self.doctype_filter:
            frappe.throw(_("Document Type is required"))

        if (
            self.doctype_event
            in ["before_transition", "after_transition", "transition_condition"]
            and not self.workflow_action
        ):
            frappe.throw(_("Workflow Action is required"))

        if self.doctype_event in [
            "has_permission",
            "has_field_permission",
        ] and self.action not in ["read", "write", "*"]:
            frappe.throw(_("Action must be 'read', 'write', or '*'"))

        # TODO: Implement
        if self.doctype_event == "has_field_permission" and self.disabled == 0:
            frappe.throw(
                _("Doctype Event '{}' is not implemented yet").format(
                    self.doctype_event
                )
            )

    def on_change(self):

        get_script_map(cached=False)

    def after_delete(self):

        get_script_map(cached=False)


def clear_script_cache():
    """
    Clear script cache.
    """
    frappe.cache.delete_value("event_script_map")


def get_script_map_key(doctype, event, action=None, workflow_action=None):
    key = f"{doctype}:{event}"
    if action:
        key = f"{key}:{action}"
    if workflow_action:
        key = f"{key}:{workflow_action}"
    return key


def get_script_map(cached=True):
    """
    Fetch or create the script map.
    """
    if frappe.flags.in_patch:
        return {}
    if not frappe.db.table_exists("Event Script") or not frappe.db.table_exists(
        "Event Script Parameter"
    ):
        return {}

    # Check if cached script map exists
    if cached:
        script_map = frappe.cache.get_value("event_script_map")
        if script_map:
            return script_map

    script_map = {}

    # Retrieve all active (non-disabled) scripts, ordered by priority
    enabled_scripts = frappe.get_all(
        "Event Script",
        filters={"disabled": 0},
        order_by="priority desc",
        fields=[
            "name",
            "user",
            "user_group",
            "role",
            "role_profile",
            "document_type",
            "document_type_group",
            "title",
            "doctype_event",
            "action",
            "workflow_action",
            "script",
            "priority",
        ],
    )

    # Process each script and build the script map
    for script in enabled_scripts:
        resolved_doctypes = []
        if script.document_type:
            resolved_doctypes.append(script.document_type)
        if script.document_type_group:
            resolved_doctypes.append(
                frappe.db.get_all(
                    "DocType Group Member",
                    filters={"parent": script.document_type_group},
                    pluck="document_type",
                )
            )
        parameters = frappe.get_all(
            "Event Script Parameter",
            filters={"parent": script.name},
            fields=["document_type", "document_name", "field"],
            order_by="idx asc",
        )
        users = {
            key: script[key]
            for key in script
            if key in ["user", "user_group", "role", "role_profile"]
        }

        for document_type in resolved_doctypes:
            events = unwrap_doctype_event(script.doctype_event)
            for event in events:
                key = get_script_map_key(
                    document_type,
                    event,
                    script.action,
                    script.workflow_action,
                )
                script_map.setdefault(key, [])
                script_map[key].append(
                    {
                        "name": f"{script.name}:{script.title}",
                        "event": key,
                        "script": script.script,
                        "parameters": parameters,
                        "users": users,
                        "priority": script.priority,
                    }
                )

    # Cache the script map and dynamic values
    frappe.cache.set_value("event_script_map", script_map)

    return script_map


@frappe.whitelist()
def get_resolved_script_map(cached=True):

    if frappe.session.user != "Administrator":
        frappe.throw(_("Must be Administrator to run this query"))

    script_map = get_script_map(cached=cached)

    for scripts in script_map.values():
        for script in scripts:
            script["_parameters"] = script["parameters"]
            script["parameters"] = resolve_parameters(script["parameters"])
            script["_users"] = script["users"]
            script["users"] = resolve_users(script["users"])

    return script_map


def unwrap_doctype_event(event):
    if event == "on_change_or_rename":
        return ["on_change", "after_rename"]
    return [event]


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


event_script_hooks = {
    "doc_events": {
        "*": {
            "on_change": ["tweaks.tweaks.doctype.event_script.event_script.on_change"]
        }
    },
    "permission_query_conditions": {
        "*": "tweaks.tweaks.doctype.event_script.event_script.get_permission_query_conditions",
    },
    "has_permission": {
        "*": "tweaks.tweaks.doctype.event_script.event_script.has_permission"
    },
    "after_install": [
        "tweaks.tweaks.doctype.event_script.event_script.create_workflow_fields"
    ],
}


def resolve_parameters(parameters):
    resolved_parameters = []
    for parameter in parameters:
        doctype = parameter.document_type or parameter.single_doctype
        docname = parameter.document_name or parameter.single_doctype
        field = parameter.field or "name"
        if "," in field:
            field = [f.strip() for f in field.split(",")]
        value = frappe.db.get_value(doctype, docname, field)
        docname = docname or doctype
        resolved_parameters.append(value)
    return resolved_parameters


def resolve_users(user_filters):

    user = user_filters.get("user", None)
    user_group = user_filters.get("user_group", None)
    role = user_filters.get("role", None)
    role_profile = user_filters.get("role_profile", None)

    resolved_users = []
    if user:
        resolved_users.append([user])
    if user_group:
        resolved_users.append(
            frappe.db.get_all(
                "User Group Member",
                filters={"parent": user_group},
                pluck="user",
            )
        )
    if role:
        resolved_users.append(
            frappe.db.get_all(
                "Has Role",
                filters={"role": role, "parenttype": "User"},
                pluck="parent",
            )
        )
    if role_profile:
        resolved_users.append(
            frappe.db.get_all(
                "User",
                filters={"role_profile_name": role_profile},
                pluck="name",
            )
        )
    if len(resolved_users) > 1:
        resolved_users = [
            x for x in resolved_users[0] if all(x in arr for arr in resolved_users[1:])
        ]
    elif len(resolved_users) == 1:
        resolved_users = resolved_users[0]
    else:
        resolved_users = ["*"]
    return set(resolved_users)


def execute_script(name, script, locals, event, throw=True):
    """
    Execute a script with provided parameters.
    """
    # Execute the script safely and handle any errors
    try:
        safe_exec.safe_exec(script, None, locals, script_filename=name)
    except Exception as e:
        frappe.log_error(f"Error executing Event Script '{name}' at '{event}'", e)
        if throw:
            raise e

    return locals


def run_method(run_method):

    def patched(self, method, *args, **kwargs):

        out = run_method(self, method, *args, **kwargs)

        user = frappe.session.user

        scripts = get_script_map().get(get_script_map_key(self.doctype, method), [])

        for script in scripts:

            allowed_users = resolve_users(script["users"])

            if not (user in allowed_users or "*" in allowed_users):
                continue

            locals = {
                "doc": self,
                "doctype": self.doctype,
                "user": user,
                "parameters": resolve_parameters(script["parameters"]),
                "event": method,
                "event_args": (
                    args if method in ["before_rename", "after_rename"] else None
                ),
            }

            execute_script(script["name"], script["script"], locals, script["event"])

        return out

    return patched


def apply_event_script_patches():

    frappe.model.document.Document.run_method = run_method(
        frappe.model.document.Document.run_method
    )
    DatabaseQuery.build_match_conditions = build_match_conditions(
        DatabaseQuery.build_match_conditions
    )
    frappe.model.workflow.is_transition_condition_satisfied = (
        is_transition_condition_satisfied
    )
    frappe.model.workflow.get_transitions = get_transitions
    frappe.model.workflow.apply_workflow = apply_workflow


def get_permission_policies(doctype, doc=None, ptype=None, user=None, debug=False):

    user = user or frappe.session.user

    scripts = get_script_map().get(
        get_script_map_key(doctype, "has_permission", ptype or "read"), []
    ) + get_script_map().get(get_script_map_key(doctype, "has_permission", "*"), [])
    scripts = sorted(scripts, key=lambda x: x["priority"], reverse=True)

    policies = []

    for script in scripts:

        allowed_users = resolve_users(script["users"])

        if not (user in allowed_users or "*" in allowed_users):
            continue

        locals = {
            "doc": doc,
            "doctype": doctype,
            "user": user,
            "parameters": resolve_parameters(script["parameters"]),
            "allow": None,
            "filters": None,
            "or_filters": None,
            "message": None,
        }

        execute_script(script["name"], script["script"], locals, script["event"])

        if locals["filters"] or locals["or_filters"] or locals["allow"] is not None:

            policies.append(
                {
                    "allow": (
                        True if locals["allow"] is None or locals["allow"] else False
                    ),
                    "filters": locals["filters"],
                    "or_filters": locals["or_filters"],
                    "message": locals["message"],
                }
            )

    if not policies and len(scripts) > 0:
        policies.append(
            {"allow": False, "message": None, "filters": None, "or_filters": None}
        )

    return policies


def get_permission_query_conditions(user=None, doctype=None, policies=None):

    if user == "Administrator":
        return ""

    policies = policies or get_permission_policies(doctype, user=user, ptype="read")

    if not policies:
        return ""

    case_conditions = []

    for policy in policies:

        if policy["filters"] or policy["or_filters"]:

            query = frappe.db.get_all(
                doctype,
                filters=policy["filters"],
                or_filters=policy["or_filters"],
                run=False,
                distinct=True,
                order_by="",
            )
            case_conditions.append(
                f"WHEN `tab{doctype}`.`name` IN ({query}) THEN {1 if policy['allow'] else 0}"
            )

        else:

            case_conditions.append(f"WHEN 1=1 THEN {1 if policy['allow'] else 0}")

    conditions = f"(CASE {' '.join(case_conditions)} ELSE 0 END = 1)"

    return conditions


@frappe.whitelist()
def inspect_permissions(doctype, doc=None, ptype=None, user=None):

    if frappe.session.user != "Administrator":
        frappe.throw("You are not allowed to inspect permissions")

    doc = doc or frappe.new_doc(doctype)
    policies = get_permission_policies(doctype, doc, ptype, user, debug=True)
    query_conditions = get_permission_query_conditions(user, doctype, policies)
    allowed = frappe.has_permission(
        doctype=doctype, ptype=ptype, doc=doc, user=user, debug=True
    )
    debug_log = "\n==============================\n".join(_pop_debug_log())
    debug_log += "\n\n" + f"Ouput of has_permission: {allowed}"
    return {
        "allowed": allowed,
        "query_conditions": query_conditions,
        "policies": policies,
        "debug_log": debug_log,
    }


def has_permission(doc=None, ptype=None, user=None, debug=False, policies=None):

    if user == "Administrator":
        return True

    policies = policies or get_permission_policies(doc.doctype, doc, ptype, user, debug)

    if not policies:
        return True

    for policy in policies:

        if policy["filters"] or policy["or_filters"]:

            filters = policy["filters"] or []
            filters = [filters] if isinstance(filters, dict) else filters
            filters.insert(0, ["name", "=", doc.name])

            exists = doc_exists(doc.doctype, filters, policy["or_filters"])
            if exists is not None:
                if not policy["allow"] and policy["message"]:
                    frappe.msgprint(_(policy["message"]))
                return policy["allow"]

        else:

            return policy["allow"]

    return False


def doc_exists(doctype, filters=None, or_filters=None):

    result = frappe.db.get_all(
        doctype, filters=filters, or_filters=or_filters, limit=1, pluck="name"
    )
    if result:
        return result[0]
    return None


def build_match_conditions(_build_match_conditions):
    """
    Patch the db_query.build_match_conditions method to include shared documents when permission query conditions are present.

    Args:
        _build_match_conditions: Original build_match_conditions function from frappe.

    Returns:
        build_match_conditions: Patched build_match_conditions function.
    """

    def build_match_conditions(self, as_condition=True) -> str | list:
        """
        Patched version of build_match_conditions to account for shared documents.

        Args:
            as_condition: Boolean indicating whether to return result as a single SQL condition or a list.

        Returns:
            str | list: Conditions for the query.
        """
        # Retrieve permission query conditions if present
        doctype_conditions = self.get_permission_query_conditions()
        if doctype_conditions:
            # Fetch shared documents if conditions are present
            self._fetch_shared_documents = True

        # Cache and override get_permission_query_conditions with the cached version
        def get_permission_query_conditions():
            return doctype_conditions

        self.get_permission_query_conditions = get_permission_query_conditions

        return _build_match_conditions(self, as_condition)

    return build_match_conditions


@frappe.whitelist()
def get_transition_conditions(doc=None, transition=None, user=None):

    user = user or frappe.session.user

    scripts = get_script_map().get(
        get_script_map_key(doc.doctype, "transition_condition", transition.action), []
    )

    policies = []

    for script in scripts:

        allowed_users = resolve_users(script["users"])

        if not (user in allowed_users or "*" in allowed_users):
            continue

        locals = {
            "doc": doc,
            "doctype": doc.doctype,
            "user": user,
            "parameters": resolve_parameters(script["parameters"]),
            "allow": None,
            "filters": None,
            "or_filters": None,
            "action": transition.action,
            "state": transition.state,
            "next_state": transition.next_state,
        }

        execute_script(script["name"], script["script"], locals, script["event"])

        if locals["filters"] or locals["or_filters"] or locals["allow"] is not None:

            policies.append(
                {
                    "allow": (
                        True if locals["allow"] is None or locals["allow"] else False
                    ),
                    "filters": locals["filters"],
                    "or_filters": locals["or_filters"],
                }
            )

    if not policies and len(scripts) > 0:
        policies.append({"allow": False})

    return policies


def is_transition_condition_satisfied(transition, doc) -> bool:

    if transition.condition:

        eval_result = safe_exec.safe_eval(
            transition.condition, safe_exec.get_safe_globals(), dict(doc=doc.as_dict())
        )

        if not eval_result:

            return False

    conditions = get_transition_conditions(doc, transition)

    if not conditions:
        return True

    for condition in conditions:

        if condition["filters"] or condition["or_filters"]:

            filters = condition["filters"]
            filters = [filters] if isinstance(filters, dict) else filters
            filters.insert(0, ["name", "=", doc.name])

            exists = doc_exists(doc.doctype, filters, condition["or_filters"])
            if exists is not None:
                if not condition["allow"] and condition["message"]:
                    frappe.msgprint(_(condition["message"]))
                return condition["allow"]

        else:
            return condition["allow"]

    return False


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

        scripts = get_script_map().get(
            get_script_map_key(doc.doctype, "before_transition", transition.action), []
        )
        for script in scripts:

            allowed_users = resolve_users(script["users"])

            if not (user in allowed_users or "*" in allowed_users):
                continue

            locals = {
                "doc": doc,
                "doctype": doc.doctype,
                "user": user,
                "parameters": resolve_parameters(script["parameters"]),
                "action": transition.action,
                "state": transition.state,
                "next_state": transition.next_state,
            }
            execute_script(script["name"], script["script"], locals, script["event"])

        doc.save(ignore_permissions=True)
        if starting_state == doc.get(f"{workflow.workflow_state_field}_starting"):
            doc.add_comment("Workflow", _(doc.get(workflow.workflow_state_field)))

        scripts = get_script_map().get(
            get_script_map_key(doc.doctype, "after_transition", transition.action), []
        )
        for script in scripts:

            allowed_users = resolve_users(script["users"])

            if not (user in allowed_users or "*" in allowed_users):
                continue

            locals = {
                "doc": doc,
                "doctype": doc.doctype,
                "user": user,
                "parameters": resolve_parameters(script["parameters"]),
                "action": transition.action,
                "state": transition.state,
                "next_state": transition.next_state,
            }
            execute_script(script["name"], script["script"], locals, script["event"])

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
