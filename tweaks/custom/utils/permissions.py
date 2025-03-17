import frappe
from frappe import _
from frappe.permissions import _pop_debug_log
from tweaks.custom.doctype.server_script_utils import get_server_script_map


def get_permission_policies(user, ptype=None, doc=None, doctype=None):

    if user == "Administrator":
        return []

    policies = []

    scripts = (
        get_server_script_map().get("permission_policy", {}).get(doctype or doc.doctype)
    )

    if not scripts:
        return []

    for script in scripts:
        script = frappe.get_doc("Server Script", script)
        if policy := script.get_permission_policy(user, ptype=ptype, doc=doc):
            policies.append(policy)

    if not policies and len(scripts) > 0:
        policies.append(frappe._dict({"allow": False}))

    return policies


def get_permission_policy_query_conditions(user=None, doctype=None, policies=None):

    if user == "Administrator":
        return ""

    policies = policies or get_permission_policies(user, doctype=doctype)

    if not policies:
        return ""

    case_conditions = []

    for policy in policies:

        if policy.query:

            case_conditions.append(
                f"WHEN `tab{doctype}`.`name` IN ({policy.query}) THEN {1 if policy['allow'] else 0}"
            )

        else:

            case_conditions.append(f"WHEN 1=1 THEN {1 if policy['allow'] else 0}")

    conditions = f"(CASE {' '.join(case_conditions)} ELSE 0 END = 1)"

    return conditions


def has_permission_policy(doc=None, ptype=None, user=None, debug=False, policies=None):

    if user == "Administrator":
        return True

    policies = policies or get_permission_policies(user, ptype=ptype, doc=doc)

    if not policies:
        return None

    for policy in policies:

        if policy.query:

            exists = frappe.db.sql(
                f"SELECT CASE WHEN %s IN ({policy.query}) THEN 1 ELSE 0 END", doc.name
            )[0][0]

            if exists:
                if not policy.allow and policy.message:
                    frappe.msgprint(_(policy.message))
                return policy.allow

        else:

            if not policy.allow and policy.message:
                frappe.msgprint(_(policy.message))

            return policy.allow

    return False


@frappe.whitelist()
def inspect_permissions(doctype=None, doc=None, ptype=None, user=None):

    doc = doc or frappe.new_doc(doctype)
    policies = get_permission_policies(user, ptype=ptype, doc=doc, doctype=doctype)
    query_conditions = get_permission_policy_query_conditions(
        doctype or doc.doctype, policies
    )
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


permission_hooks = {
    "permission_query_conditions": {
        "*": ["tweaks.custom.utils.permissions.get_permission_policy_query_conditions"]
    },
    "has_permission": {"*": ["tweaks.custom.utils.permissions.has_permission_policy"]},
}
