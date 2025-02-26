import frappe
from tweaks.custom.doctype.client_script import (
    create_custom_client_script_fields,
    set_custom_client_script_properties,
)


def execute():

    delete_old_fields()
    create_custom_client_script_fields()
    set_custom_client_script_properties()


def delete_old_fields():

    fields = frappe.db.get_all(
        "Custom Field",
        {
            "dt": "Client Script",
            "fieldname": ["in", ["dtgroup", "safe_title"]],
            "is_system_generated": 1,
        },
        pluck="name",
    )
    for field in fields:
        field = frappe.get_doc("Custom Field", field)
        field.delete()
