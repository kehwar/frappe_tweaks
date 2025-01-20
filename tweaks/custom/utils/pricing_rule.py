import frappe
import frappe.utils
import frappe.utils.safe_exec
from erpnext.accounts.doctype.pricing_rule import utils
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def create_pricing_rule_fields():

    create_custom_fields(
        {
            "Pricing Rule": [
                {
                    "fieldname": "script",
                    "fieldtype": "Code",
                    "options": "Python",
                    "label": "Script",
                    "insert_after": "dynamic_condition_tab",
                }
            ]
        },
        ignore_validate=True,
    )


pricing_rule_hooks = {
    "after_install": ["tweaks.custom.utils.pricing_rule.create_pricing_rule_fields"],
}


def filter_pricing_rule_based_on_condition(pricing_rules, doc=None):
    filtered_pricing_rules = []
    if doc:
        for pricing_rule in pricing_rules:

            if pricing_rule.condition:
                try:
                    if not frappe.safe_eval(
                        pricing_rule.condition, None, doc.as_dict()
                    ):
                        continue
                except Exception:
                    continue

            if pricing_rule.script:

                try:

                    locals = {
                        "doc": doc,
                        "doctype": doc.get("doctype"),
                        "pricing_rule": pricing_rule,
                        "user": frappe.session.user,
                        "allow": True,
                    }

                    frappe.utils.safe_exec.safe_exec(
                        pricing_rule.script,
                        None,
                        locals,
                        script_filename=f"{pricing_rule.name}:{pricing_rule.title}",
                    )

                    pricing_rule = locals["pricing_rule"] or pricing_rule

                    if not locals["allow"]:
                        continue

                except Exception as e:
                    frappe.log_error(
                        f"Error executing Pricing Rule Script '{pricing_rule.name}:{pricing_rule.title}'",
                        e,
                    )
                    continue

            filtered_pricing_rules.append(pricing_rule)
    else:
        filtered_pricing_rules = pricing_rules

    return filtered_pricing_rules


def apply_pricing_rule_patches():

    utils.filter_pricing_rule_based_on_condition = (
        filter_pricing_rule_based_on_condition
    )
