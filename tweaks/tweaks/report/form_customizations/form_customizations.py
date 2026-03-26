# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    """
    Form Customizations Report

    Aggregates Custom Fields and Property Setters to show all customizations.
    - One row for each Custom Field
    - Property Setters aggregated by DocType (if applied on doctype) or DocType/Fieldname (if applied on DocField)

    Filters:
        doctype (optional): Filter by DocType
        module (optional): Filter by Module
        customization_type (optional): Filter by "Custom Field" or "Property Setter"

    Columns:
        - Customization Type: "Custom Field" or "Property Setter"
        - DocType: The DocType being customized
        - Field Name: Field name (for Custom Fields) or aggregation key (for Property Setters)
        - Label: Field label (for Custom Fields)
        - Field Type: Field type (for Custom Fields)
        - Property Count: Number of property setters (for Property Setters)
        - Properties: Aggregated properties (for Property Setters)
        - Module: Module of the customization
        - Is System Generated: Whether the customization is system generated

    Features:
        - Combines Custom Fields and Property Setters in one view
        - Aggregates Property Setters by DocType or DocType/Fieldname
        - Filter by doctype, module, or customization type
        - Clickable links to open DocType documents

    Permissions:
        Requires System Manager role

    Related:
        - Custom Field DocType: frappe/custom/doctype/custom_field/
        - Property Setter DocType: frappe/custom/doctype/property_setter/
    """
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


def get_columns(filters):
    """Define report columns"""
    columns = [
        {
            "fieldname": "doctype_module",
            "label": _("Module (DocType)"),
            "fieldtype": "Link",
            "options": "Module Def",
            "width": 140,
        },
        {
            "fieldname": "dt",
            "label": _("DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 180,
        },
        {
            "fieldname": "customization_type",
            "label": _("Customization Type"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "doctype_or_field",
            "label": _("Applied For"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "fieldname",
            "label": _("Field Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "property",
            "label": _("Property"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "value",
            "label": _("Value"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "customization_module",
            "label": _("Module (Customization)"),
            "fieldtype": "Link",
            "options": "Module Def",
            "width": 140,
        },
        {
            "fieldname": "customization_name",
            "label": _("Customization Name"),
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1,
        },
    ]

    if filters.get("show_system_generated"):
        columns.append(
            {
                "fieldname": "is_system_generated",
                "label": _("System Generated"),
                "fieldtype": "Check",
                "width": 140,
            }
        )

    if filters.get("show_ui_fields"):
        columns.append(
            {
                "fieldname": "fieldtype",
                "label": _("Field Type"),
                "fieldtype": "Data",
                "width": 140,
            }
        )

    if filters.get("show_custom_doctype"):
        columns.append(
            {
                "fieldname": "is_custom_doctype",
                "label": _("Custom DocType"),
                "fieldtype": "Check",
                "width": 140,
            }
        )

    return columns


def get_data(filters):
    """Get Custom Fields and Property Setters data"""
    data = []
    filters = filters or {}

    # Add Custom Fields (always DocField — skip if filter requests DocType only)
    if (
        not filters.get("customization_type")
        or filters.get("customization_type") == "Custom Field"
    ) and filters.get("doctype_or_field") != "DocType":
        data.extend(get_custom_fields(filters))

    # Add Property Setters
    if (
        not filters.get("customization_type")
        or filters.get("customization_type") == "Property Setter"
    ):
        data.extend(get_property_setters(filters))

    # Sort by DocType, fieldname, property
    data.sort(
        key=lambda x: (x["dt"], x.get("fieldname") or "", x.get("property") or "")
    )

    # Batch-fetch DocType module for all unique dt values
    unique_dts = {row["dt"] for row in data}
    dt_module_map = {
        d["name"]: d["module"]
        for d in frappe.get_all(
            "DocType",
            filters={"name": ["in", list(unique_dts)]},
            fields=["name", "module"],
        )
    }
    for row in data:
        row["doctype_module"] = dt_module_map.get(row["dt"], "")

    if filters.get("show_custom_doctype"):
        custom_dt_set = {
            d["name"]
            for d in frappe.get_all(
                "DocType",
                filters={"name": ["in", list(dt_module_map)], "custom": 1},
                fields=["name"],
            )
        }
        for row in data:
            row["is_custom_doctype"] = 1 if row["dt"] in custom_dt_set else 0

    return data


def get_custom_fields(filters):
    """Get Custom Fields data"""
    filter_dict = {}

    if filters.get("doctype"):
        filter_dict["dt"] = filters.get("doctype")

    if filters.get("customization_module"):
        filter_dict["module"] = filters.get("customization_module")

    if not filters.get("show_system_generated"):
        filter_dict["is_system_generated"] = 0

    custom_fields = frappe.get_all(
        "Custom Field",
        filters=filter_dict,
        fields=[
            "dt",
            "fieldname",
            "fieldtype",
            "label",
            "module",
            "name",
            "is_system_generated",
        ],
        order_by="dt, fieldname",
    )

    # Process the data to match the report format
    result = []
    ui_field_types = ["Column Break", "Section Break", "Tab Break"]

    for field in custom_fields:
        # Skip UI fields if show_ui_fields is not checked
        if (
            not filters.get("show_ui_fields")
            and field.get("fieldtype") in ui_field_types
        ):
            continue

        field["customization_type"] = "Custom Field"
        field["property"] = ""
        field["value"] = ""
        field["customization_name"] = field["name"]
        field["doctype_or_field"] = "DocField"
        field["customization_module"] = field.pop("module", None)
        result.append(field)

    return result


def get_property_setters(filters):
    """Get Property Setters data, one row per property setter"""
    filter_dict = {}

    if filters.get("doctype"):
        filter_dict["doc_type"] = filters.get("doctype")

    if filters.get("customization_module"):
        filter_dict["module"] = filters.get("customization_module")

    if not filters.get("show_system_generated"):
        filter_dict["is_system_generated"] = 0

    if filters.get("doctype_or_field"):
        filter_dict["doctype_or_field"] = filters.get("doctype_or_field")

    property_setters = frappe.get_all(
        "Property Setter",
        filters=filter_dict,
        fields=[
            "name",
            "doc_type",
            "doctype_or_field",
            "field_name",
            "row_name",
            "property",
            "value",
            "module",
            "is_system_generated",
        ],
        order_by="doc_type, field_name, property",
    )

    result = []
    for ps in property_setters:
        fieldname = (
            ""
            if ps["doctype_or_field"] == "DocType"
            else (ps.get("field_name") or ps.get("row_name") or "")
        )
        result.append(
            {
                "customization_type": "Property Setter",
                "dt": ps["doc_type"],
                "fieldname": fieldname,
                "property": ps["property"],
                "value": ps["value"] or "",
                "customization_module": ps["module"],
                "customization_name": ps["name"],
                "doctype_or_field": ps["doctype_or_field"],
                "is_system_generated": ps.get("is_system_generated", 0),
                "fieldtype": "",
            }
        )

    return result
