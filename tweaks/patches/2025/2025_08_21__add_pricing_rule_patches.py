from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():

    create_pricing_rule_custom_fields()


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
