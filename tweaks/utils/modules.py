# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

"""
Module utilities for tweaks app
"""

import os
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Union

import frappe
from frappe import get_module_path, scrub
from frappe.modules.utils import get_app_publisher, get_doc_path
from frappe.utils import cstr, now_datetime

if TYPE_CHECKING:
    from frappe.model.document import Document


def make_boilerplate(
    template: str,
    doc: Union["Document", "frappe._dict"],
    opts: Union[dict, "frappe._dict"] = None,
    template_module: str = None,
    template_doctype: str = None,
):
    """
    Create boilerplate files from templates.

    This is similar to frappe.modules.utils.make_boilerplate but allows
    specifying custom template locations instead of hardcoding to frappe/core.

    Args:
        template: Template filename (e.g., "controller.py")
        doc: Document or dict with module, doctype, name
        opts: Additional options for template formatting
        template_module: Module where template is located (default: same as doc.module)
        template_doctype: DocType folder where template is located (default: same as doc.doctype)
    """
    target_path = get_doc_path(doc.module, doc.doctype, doc.name)
    template_name = template.replace("controller", scrub(doc.name))
    if template_name.endswith("._py"):
        template_name = template_name[:-4] + ".py"
    target_file_path = os.path.join(target_path, template_name)

    # Use provided template location or default to same module/doctype
    template_module = template_module or doc.module
    template_doctype = template_doctype or doc.doctype

    template_file_path = os.path.join(
        get_module_path(template_module),
        "doctype",
        scrub(template_doctype),
        "boilerplate",
        template,
    )

    if os.path.exists(target_file_path):
        print(f"{target_file_path} already exists, skipping...")
        return

    doc = doc or frappe._dict()
    opts = opts or frappe._dict()
    app_publisher = get_app_publisher(doc.module)
    base_class = "Document"
    base_class_import = "from frappe.model.document import Document"
    controller_body = "pass"

    if doc.get("is_tree"):
        base_class = "NestedSet"
        base_class_import = "from frappe.utils.nestedset import NestedSet"

    if doc.get("is_virtual"):
        controller_body = indent(
            dedent(
                """
			def db_insert(self, *args, **kwargs):
				pass

			def load_from_db(self):
				pass

			def db_update(self):
				pass

			@staticmethod
			def get_list(args):
				pass

			@staticmethod
			def get_count(args):
				pass

			@staticmethod
			def get_stats(args):
				pass
			"""
            ),
            "\t",
        )

    with open(target_file_path, "w") as target, open(template_file_path) as source:
        template_content = source.read()
        controller_file_content = cstr(template_content).format(
            app_publisher=app_publisher,
            year=now_datetime().year,
            classname=doc.name.replace(" ", "").replace("-", ""),
            base_class_import=base_class_import,
            base_class=base_class,
            doctype=doc.name,
            **opts,
            custom_controller=controller_body,
        )
        target.write(frappe.as_unicode(controller_file_content))
