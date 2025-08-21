import frappe
from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules
from frappe.utils.safe_exec import safe_exec


def get_product_discount_rule(
    pricing_rule, item_details, args=None, doc=None, _hook=None
):
    """
    Hook to post process `get_product_discount_rule`
    """
    if not (pricing_rule_name := pricing_rule.get("name")):
        return

    if not (pricing_rule_dynamic_free_item := pricing_rule.get("dynamic_free_item")):
        return

    if not item_details.free_item_data:
        return

    for item in item_details.free_item_data:
        if str(item.get("pricing_rules")) == pricing_rule_name:
            safe_exec(
                pricing_rule_dynamic_free_item,
                None,
                {"item": item, "pricing_rule": pricing_rule, "doc": doc},
            )
            print(item)


def apply_pricing_rule_on_transaction(doc, _hook=None):

    applied_pricing_rules = {}
    free_item_data = []

    for item in doc.items:

        pricing_rules = get_applied_pricing_rules(item.pricing_rules)
        for pricing_rule in pricing_rules:
            applied_pricing_rules.setdefault(pricing_rule, []).append(item)

        if item.is_free_item:
            free_item_data.append(item)

    doc.free_item_data = free_item_data

    doc.applied_pricing_rules = applied_pricing_rules

    for pricing_rule in applied_pricing_rules.keys():

        pricing_rule_doc = frappe.get_cached_doc("Pricing Rule", pricing_rule)

        if pricing_rule_doc.dynamic_validation:

            pricing_rule_doc.document_items = applied_pricing_rules[pricing_rule]

            safe_exec(
                pricing_rule_doc.dynamic_validation,
                None,
                {"doc": doc, "pricing_rule": pricing_rule_doc},
            )


def install_pricing_rule_customizations():

    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    def create_pricing_rule_custom_fields():

        create_custom_fields(
            {
                "Pricing Rule": [
                    {
                        "label": "Tweaks",
                        "fieldname": "tweaks_section",
                        "insert_after": "condition",
                        "fieldtype": "Section Break",
                    },
                    {
                        "label": "Dynamic Free Item",
                        "fieldname": "dynamic_free_item",
                        "insert_after": "tweaks_section",
                        "fieldtype": "Code",
                        "options": "Python",
                        "depends_on": "eval:doc.price_or_product_discount == 'Product'",
                        "description": "<p>\n<b>API</b>\n<br>\n<li>\n<code>item</code>: free item\n<li><code>pricing_rule</code>: pricing rule\n<li><code>doc</code>: document\n</p>\n<p><b>Example</b>\n<pre>\nitem.update({\n    'qty': 10\n})\n</pre>\n</p>",
                    },
                    {
                        "label": "Dynamic Validation",
                        "fieldname": "dynamic_validation",
                        "insert_after": "dynamic_free_item",
                        "fieldtype": "Code",
                        "options": "Python",
                        "description": "<p>\n<b>API</b>\n<br>\n<li><code>doc</code>: document\n<li><code>doc.applied_pricing_rules</code>: document items grouped by their pricing rule\n<li><code>doc.free_item_data</code>: free items in document\n<li><code>pricing_rule</code>: pricing rule\n<li><code>pricing_rule.document_items</code>: document items that apply the pricing rule\n</p>\n<p><b>Example</b>\n<pre>\nif (doc.free_item_data):\n    frappe.throw()\n</pre>\n</p>",
                    },
                ]
            },
        )

    create_pricing_rule_custom_fields()
