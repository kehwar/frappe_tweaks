from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def apply_role_patches():

    make_property_setter(
        doctype="Role",
        fieldname=None,
        property="allow_rename",
        value="1",
        property_type="Check",
        for_doctype=True,
    )
