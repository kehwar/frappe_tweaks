import frappe
from frappe import _
from frappe.custom.doctype.client_script.client_script import ClientScript
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.form.meta import FormMeta
from frappe.modules import scrub
from tweaks.custom.doctype.customize_form import (
    set_property_setters_for_actions_and_links,
)


class TweaksClientScript(ClientScript):

    def before_validate(self):
        if self.view == "Global":
            self.dt = None

    def validate(self):
        if self.view != "Global" and not self.dt:
            frappe.throw(_("DocType is required"))


def apply_client_script_patches():
    FormMeta.add_custom_script = add_custom_script


def create_custom_client_script_fields():
    create_custom_fields(
        {
            "Client Script": [
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
                    "options": "Client Script",
                    "insert_after": "module",
                },
                {
                    "fieldname": "priority",
                    "label": "Priority",
                    "fieldtype": "Int",
                    "default": "100",
                    "insert_after": "reference_script",
                },
            ]
        },
    )


def set_custom_client_script_properties():
    make_property_setter(
        "Client Script",
        "view",
        "options",
        "List\nForm\nGlobal",
        "Select",
    )
    make_property_setter(
        "Client Script",
        "view",
        "in_standard_filter",
        "1",
        "Check",
    )
    make_property_setter(
        "Client Script",
        "view",
        "set_only_once",
        "1",
        "Check",
    )
    make_property_setter(
        "Client Script",
        "dt",
        "reqd",
        "0",
        "Check",
    )
    make_property_setter(
        "Client Script",
        "dt",
        "depends_on",
        "eval:doc.view != 'Global'",
        "Data",
    )
    make_property_setter(
        "Client Script",
        "dt",
        "mandatory_depends_on",
        "eval:doc.view != 'Global'",
        "Data",
    )
    make_property_setter(
        "Client Script", None, "autoname", "hash", "Data", for_doctype=True
    )
    make_property_setter(
        "Client Script", None, "title_field", "title", "Data", for_doctype=True
    )
    make_property_setter(
        "Client Script",
        None,
        "show_title_field_in_link",
        "1",
        "Check",
        for_doctype=True,
    )
    make_property_setter(
        "Client Script",
        None,
        "search_fields",
        "dt, view",
        "Data",
        for_doctype=True,
    )
    set_property_setters_for_actions_and_links(
        "Client Script",
        links=[
            {
                "link_doctype": "Client Script",
                "link_fieldname": "reference_script",
            }
        ],
    )


def add_custom_script(self):
    """embed all require files"""
    # custom script
    client_scripts = frappe.get_all(
        "Client Script",
        filters=[["enabled", "=", 1], ["dt", "=", self.name]],
        fields=["name", "title", "script", "view"],
        order_by="priority desc, title asc",
    )

    list_script = ""
    form_script = ""
    for script in client_scripts:
        if not script.script:
            continue

        if script.view in "List":
            list_script += f"""
// {script.title} - {script.name}
{script.script}

"""

        if script.view in "Form":
            form_script += f"""
// {script.title} - {script.name}
{script.script}

"""

    file = scrub(self.name)
    form_script += f"\n\n//# sourceURL={file}__custom_js"
    list_script += f"\n\n//# sourceURL={file}__custom_list_js"

    self.set("__custom_js", form_script)
    self.set("__custom_list_js", list_script)


client_script_hooks = {
    "after_install": [
        "tweaks.custom.doctype.client_script.create_custom_client_script_fields",
        "tweaks.custom.doctype.client_script.set_custom_client_script_properties",
    ],
}


@frappe.whitelist()
def get_global_script():

    client_scripts = frappe.get_all(
        "Client Script",
        filters={"view": "Global"},
        fields=["name", "title", "script", "view"],
        order_by="priority desc, title asc",
    )

    global_script = ""
    for script in client_scripts:
        if not script.script:
            continue

        global_script += f"""
// {script.title} - {script.name}
{script.script}

"""

    file = "app"
    global_script += f"\n\n//# sourceURL={file}__custom_js"

    return global_script
