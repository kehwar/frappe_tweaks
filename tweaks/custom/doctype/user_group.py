from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def apply_user_group_patches():

    make_property_setter(
        "User Group",  # doctype
        None,  # fieldname
        "allow_rename",  # property
        "1",  # value
        "Check",  # property_type
        True,  # for_doctype
    )
