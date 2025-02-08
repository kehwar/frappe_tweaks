import frappe
from frappe import _
from frappe.custom.doctype.client_script.client_script import ClientScript
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.form.meta import FormMeta
from frappe.modules import scrub
from tweaks.custom.utils.formatter import to_snake_case


class TweaksClientScript(ClientScript):

    def before_validate(self):
        self.set(
            "safe_title",
            "__".join(
                [
                    to_snake_case(self.dt or self.dtgroup or "app"),
                    to_snake_case(self.title),
                ]
            ),
        )
        if self.dt and self.dtgroup:
            self.dt = None

        if self.view == "Global":
            self.dt = None
            self.dtgroup = None

    def validate(self):
        if self.view != "Global" and not (self.dt or self.dtgroup):
            frappe.throw(_("DocType or DocType Group is required"))

    def on_update(self):
        self.clear_doctype_cache()

    def on_trash(self):
        self.clear_doctype_cache()

    def clear_doctype_cache(self):
        if self.dtgroup:
            dtgroupmembers = frappe.db.get_all(
                "DocType Group Member", filters={"parent": "New"}, pluck="document_type"
            )
            for dt in dtgroupmembers:
                frappe.clear_cache(doctype=dt)
        elif self.dt:
            frappe.clear_cache(doctype=self.dt)


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
                    "fieldname": "dtgroup",
                    "label": "DocType group",
                    "fieldtype": "Link",
                    "options": "DocType Group",
                    "insert_after": "dt",
                    "set_only_once": 1,
                    "depends_on": "eval:!doc.dt && doc.view != 'Global'",
                    "in_standard_filter": 1,
                },
                {
                    "fieldname": "safe_title",
                    "label": "Safe title",
                    "fieldtype": "Data",
                    "insert_after": "title",
                    "read_only": 1,
                },
                {
                    "fieldname": "priority",
                    "label": "Priority",
                    "fieldtype": "Int",
                    "default": "100",
                    "insert_after": "module",
                },
            ]
        },
    )


def set_custom_client_script_properties():
    make_property_setter(
        "Client Script",
        "view",
        "options",
        "List\nForm\nRepeat in both\nGlobal",
        "Select",
    )
    make_property_setter(
        "Client Script",
        "view",
        "set_only_once",
        "0",
        "Check",
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
        "dt",
        "reqd",
        "0",
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
        "eval:!doc.dtgroup && doc.view != 'Global'",
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


def add_custom_script(self):

    doctype_groups = frappe.db.get_all(
        "DocType Group Member",
        filters={"document_type": self.name},
        pluck="parent",
        distinct=1,
    )

    """embed all require files"""
    # custom script
    client_scripts = frappe.get_all(
        "Client Script",
        filters=[["enabled", "=", 1]],
        or_filters=[
            ["dt", "=", self.name],
            ["dtgroup", "in", doctype_groups],
        ],
        fields=["name", "title", "script", "view"],
        order_by="priority desc, title asc",
    )

    list_script = ""
    form_script = ""
    for script in client_scripts:
        if not script.script:
            continue

        if script.view in ["List", "Repeat in both"]:
            list_script += f"""
// {script.title} - {script.name}
{script.script}

"""

        if script.view in ["Form", "Repeat in both"]:
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
