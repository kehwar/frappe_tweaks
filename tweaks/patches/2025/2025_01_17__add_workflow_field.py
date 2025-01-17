from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():

    create_custom_fields({
        "Workflow Transition": [
            {
				"fieldname": "auto_apply",
				"fieldtype": "Check",
				"label": "Auto Apply",
                "insert_after": "allow_self_approval"
            }
        ]
    }, ignore_validate=True)