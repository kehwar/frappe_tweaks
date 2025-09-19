from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def apply_role_patches():

    make_property_setter(
        "Role",  # doctype
        None,  # fieldname
        "allow_rename",  # property
        "1",  # value
        "Check",  # property_type
        True,  # for_doctype
    )
