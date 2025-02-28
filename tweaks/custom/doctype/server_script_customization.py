import frappe
import frappe.model
from frappe import handler
from frappe.core.doctype.server_script import server_script_utils
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model import db_query, document
from tweaks.custom.doctype.customize_form import (
    set_property_setters_for_actions_and_links,
)
from tweaks.custom.doctype.server_script_utils import (
    EVENT_MAP,
    get_server_script_map,
    run_server_script_for_doc_event,
)


def apply_server_script_patches():

    # get_server_script_map
    server_script_utils.get_server_script_map = get_server_script_map
    handler.get_server_script_map = get_server_script_map
    db_query.get_server_script_map = get_server_script_map

    # run_server_script_for_doc_event
    server_script_utils.run_server_script_for_doc_event = (
        run_server_script_for_doc_event
    )
    document.run_server_script_for_doc_event = run_server_script_for_doc_event


def create_custom_server_script_fields():
    create_custom_fields(
        {
            "Server Script": [
                {
                    "fieldname": "title",
                    "label": "Title",
                    "fieldtype": "Data",
                    "reqd": 1,
                },
                {
                    "fieldname": "reference_script",
                    "label": "Reference Script",
                    "fieldtype": "Link",
                    "options": "Server Script",
                    "insert_after": "module",
                },
                {
                    "fieldname": "priority",
                    "label": "Priority",
                    "fieldtype": "Int",
                    "default": "100",
                    "insert_after": "reference_script",
                    "depends_on": "eval:['DocType Event', 'Permission Policy'].includes(doc.script_type)",
                    "in_list_view": 1,
                },
                {
                    "fieldname": "description",
                    "label": "Description",
                    "fieldtype": "Text Editor",
                    "insert_after": "script",
                },
            ]
        },
    )


def set_custom_server_script_properties():
    make_property_setter(
        "Server Script", None, "autoname", "hash", "Data", for_doctype=True
    )
    make_property_setter(
        "Server Script", None, "title_field", "title", "Data", for_doctype=True
    )
    make_property_setter(
        "Server Script",
        None,
        "show_title_field_in_link",
        "1",
        "Check",
        for_doctype=True,
    )
    make_property_setter(
        "Server Script",
        None,
        "search_fields",
        "reference_doctype, script_type, api_method, doctype_event",
        "Data",
        for_doctype=True,
    )
    make_property_setter(
        "Server Script",
        "script_type",
        "options",
        "DocType Event\nScheduler Event\nPermission Policy\nPermission Query\nAPI",
        "Small Text",
    )
    make_property_setter(
        "Server Script",
        "doctype_event",
        "options",
        "\n".join(EVENT_MAP.values()),
        "Small Text",
    )
    make_property_setter(
        "Server Script",
        "reference_doctype",
        "depends_on",
        "eval:['DocType Event', 'Permission Policy', 'Permission Query'].includes(doc.script_type)",
        "Data",
    )
    make_property_setter(
        "Server Script",
        "doctype_event",
        "in_list_view",
        1,
        "Check",
    )
    make_property_setter(
        "Server Script",
        "doctype_event",
        "in_standard_filter",
        1,
        "Check",
    )
    make_property_setter(
        "Server Script",
        "api_method",
        "in_list_view",
        1,
        "Check",
    )
    make_property_setter(
        "Server Script",
        "api_method",
        "in_standard_filter",
        1,
        "Check",
    )
    set_property_setters_for_actions_and_links(
        "Server Script",
        links=[
            {
                "link_doctype": "Server Script",
                "link_fieldname": "reference_script",
            }
        ],
    )


server_script_hooks = {
    "after_install": [
        "tweaks.custom.doctype.server_script.create_custom_server_script_fields",
        "tweaks.custom.doctype.server_script.set_custom_server_script_properties",
    ],
}
