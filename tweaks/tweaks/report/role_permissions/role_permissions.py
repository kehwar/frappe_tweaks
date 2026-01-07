# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _


def execute(filters=None):
    """Generate comparison report of DocPerm vs Custom DocPerm"""
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "fieldname": "doctype",
            "label": _("DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 200,
        },
        {
            "fieldname": "role",
            "label": _("Role"),
            "fieldtype": "Link",
            "options": "Role",
            "width": 150,
        },
        {
            "fieldname": "permlevel",
            "label": _("Level"),
            "fieldtype": "Int",
            "width": 60,
        },
        {
            "fieldname": "if_owner",
            "label": _("If Owner"),
            "fieldtype": "Check",
            "width": 80,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "default_permissions",
            "label": _("Default Permissions"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "current_permissions",
            "label": _("Current Permissions"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "doctype_type",
            "label": _("Type"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "module",
            "label": _("Module"),
            "fieldtype": "Link",
            "options": "Module Def",
            "width": 120,
        },
    ]


def get_data(filters):
    """Get comparison data between default and custom permissions"""
    # Get filter values
    doctype_filter = filters.get("doctype") if filters else None
    role_filter = filters.get("role") if filters else None
    status_filter = filters.get("status") if filters else None
    doctype_type_filter = filters.get("doctype_type") if filters else None
    module_filter = filters.get("module") if filters else None

    # Permission fields to compare
    permission_fields = [
        "select",
        "read",
        "write",
        "create",
        "delete",
        "submit",
        "cancel",
        "amend",
        "report",
        "export",
        "import",
        "print",
        "email",
        "share",
    ]

    # Get all default permissions (DocPerm)
    default_perms = {}
    default_perm_query = """
        SELECT 
            parent as doctype, role, permlevel, if_owner,
            `select`, `read`, `write`, `create`, `delete`,
            submit, cancel, amend, report, export,
            `import`, `print`, email, share
        FROM `tabDocPerm`
        WHERE docstatus = 0
    """

    if doctype_filter:
        default_perm_query += f" AND parent = {frappe.db.escape(doctype_filter)}"
    if role_filter:
        default_perm_query += f" AND role = {frappe.db.escape(role_filter)}"

    for perm in frappe.db.sql(default_perm_query, as_dict=True):
        key = (perm.doctype, perm.role, perm.permlevel, perm.if_owner)
        default_perms[key] = perm

    # Get all custom permissions (Custom DocPerm)
    custom_perms = {}
    custom_perm_query = """
        SELECT 
            parent as doctype, role, permlevel, if_owner,
            `select`, `read`, `write`, `create`, `delete`,
            submit, cancel, amend, report, export,
            `import`, `print`, email, share
        FROM `tabCustom DocPerm`
    """

    if doctype_filter:
        custom_perm_query += f" WHERE parent = {frappe.db.escape(doctype_filter)}"
        if role_filter:
            custom_perm_query += f" AND role = {frappe.db.escape(role_filter)}"
    elif role_filter:
        custom_perm_query += f" WHERE role = {frappe.db.escape(role_filter)}"

    for perm in frappe.db.sql(custom_perm_query, as_dict=True):
        key = (perm.doctype, perm.role, perm.permlevel, perm.if_owner)
        custom_perms[key] = perm

    # Get doctypes with custom permissions to determine which defaults are still active
    doctypes_with_custom = frappe.db.sql_list(
        "SELECT DISTINCT parent FROM `tabCustom DocPerm`"
    )

    # Get doctype metadata (custom, is_virtual)
    all_doctypes = set(default_perms.keys()) | set(custom_perms.keys())
    doctype_names = {key[0] for key in all_doctypes}
    doctype_metadata = {}

    if doctype_names:
        metadata_query = """
            SELECT 
                name,
                module,
                custom,
                is_virtual
            FROM `tabDocType`
            WHERE name IN ({})
        """.format(
            ", ".join([frappe.db.escape(dt) for dt in doctype_names])
        )

        for meta in frappe.db.sql(metadata_query, as_dict=True):
            if meta.get("is_virtual"):
                doctype_type = "Virtual"
            elif meta.get("custom"):
                doctype_type = "Custom"
            else:
                doctype_type = "Standard"
            doctype_metadata[meta.name] = {
                "type": doctype_type,
                "module": meta.get("module", ""),
            }

    # Build comparison data
    data = []
    all_keys = set(default_perms.keys()) | set(custom_perms.keys())

    for key in sorted(all_keys):
        doctype, role, permlevel, if_owner = key
        default_perm = default_perms.get(key)
        custom_perm = custom_perms.get(key)

        # Apply doctype_type filter if specified
        if doctype_type_filter:
            current_metadata = doctype_metadata.get(doctype, {})
            current_doctype_type = (
                current_metadata.get("type")
                if isinstance(current_metadata, dict)
                else "Unknown"
            )
            if current_doctype_type != doctype_type_filter:
                continue

        # Apply module filter if specified
        if module_filter:
            current_metadata = doctype_metadata.get(doctype, {})
            current_module = (
                current_metadata.get("module")
                if isinstance(current_metadata, dict)
                else ""
            )
            if current_module != module_filter:
                continue

        # Determine status
        if doctype in doctypes_with_custom:
            # This doctype has custom permissions
            if custom_perm and default_perm:
                # Both exist - check if they differ
                is_different = any(
                    custom_perm.get(field) != default_perm.get(field)
                    for field in permission_fields
                )
                status = "Custom" if is_different else "Standard"
            else:
                status = "Custom"
        else:
            # No custom permissions for this doctype - using default
            status = "Standard"

        # Apply status filter if specified
        if status_filter and status != status_filter:
            continue

        # Get permission lists for display
        default_perms_list = []
        current_perms_list = []

        if default_perm:
            default_perms_list = [
                field.replace("_", " ").title()
                for field in permission_fields
                if default_perm.get(field)
            ]

        if custom_perm:
            current_perms_list = [
                field.replace("_", " ").title()
                for field in permission_fields
                if custom_perm.get(field)
            ]
        elif doctype not in doctypes_with_custom and default_perm:
            # If no custom perms exist for doctype, current = default
            current_perms_list = default_perms_list.copy()

        data.append(
            {
                "doctype": doctype,
                "doctype_type": (
                    doctype_metadata.get(doctype, {}).get("type")
                    if isinstance(doctype_metadata.get(doctype), dict)
                    else doctype_metadata.get(doctype, "Unknown")
                ),
                "module": (
                    doctype_metadata.get(doctype, {}).get("module")
                    if isinstance(doctype_metadata.get(doctype), dict)
                    else ""
                ),
                "role": role,
                "permlevel": permlevel,
                "if_owner": if_owner,
                "status": status,
                "default_permissions": (
                    ", ".join(default_perms_list) if default_perms_list else ""
                ),
                "current_permissions": (
                    ", ".join(current_perms_list) if current_perms_list else ""
                ),
            }
        )

    return data
