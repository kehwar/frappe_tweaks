from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def apply_role_patches():

    make_property_setter(
        doctype="Role",
        property="allow_rename",
        property_type="Check",
        value="1",
        for_doctype=True,
    )
