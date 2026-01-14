# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    """
    Customizations Report

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
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Define report columns"""
    return [
        {
            "fieldname": "dt",
            "label": _("DocType"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 180,
        },
        {
            "fieldname": "fieldname",
            "label": _("Field Name / Key"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "customization_type",
            "label": _("Customization Type"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "properties",
            "label": _("Properties"),
            "fieldtype": "Small Text",
            "width": 300,
        },
        {
            "fieldname": "module",
            "label": _("Module"),
            "fieldtype": "Link",
            "options": "Module Def",
            "width": 120,
        },
        {
            "fieldname": "custom_field_name",
            "label": _("Custom Field Name"),
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1,
        },
        {
            "fieldname": "doctype_or_field",
            "label": _("Applied For"),
            "fieldtype": "Data",
            "width": 0,
            "hidden": 1,
        },
    ]


def get_data(filters):
    """Get Custom Fields and Property Setters data"""
    data = []
    filters = filters or {}

    # Add Custom Fields
    if (
        not filters.get("customization_type")
        or filters.get("customization_type") == "Custom Field"
    ):
        data.extend(get_custom_fields(filters))

    # Add Property Setters
    if (
        not filters.get("customization_type")
        or filters.get("customization_type") == "Property Setter"
    ):
        data.extend(get_property_setters(filters))

    # Sort by DocType
    data.sort(key=lambda x: (x["dt"], x["fieldname"]))

    return data


def get_custom_fields(filters):
    """Get Custom Fields data"""
    filter_dict = {}

    if filters.get("doctype"):
        filter_dict["dt"] = filters.get("doctype")

    if filters.get("module"):
        filter_dict["module"] = filters.get("module")

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
        ],
        order_by="dt, fieldname",
    )

    # Process the data to match the report format
    for field in custom_fields:
        field["customization_type"] = "Custom Field"

        # Build properties string
        props = []
        if field.get("fieldtype"):
            props.append(f"fieldtype={field['fieldtype']}")
        if field.get("label"):
            props.append(f"label={field['label']}")
        field["properties"] = "; ".join(props)

        field["custom_field_name"] = field["name"]

    return custom_fields


def get_property_setters(filters):
    """Get Property Setters data, aggregated by DocType or DocType/Fieldname"""
    filter_dict = {}

    if filters.get("doctype"):
        filter_dict["doc_type"] = filters.get("doctype")

    if filters.get("module"):
        filter_dict["module"] = filters.get("module")

    if not filters.get("show_system_generated"):
        filter_dict["is_system_generated"] = 0

    property_setters = frappe.get_all(
        "Property Setter",
        filters=filter_dict,
        fields=[
            "doc_type",
            "doctype_or_field",
            "field_name",
            "row_name",
            "property",
            "value",
            "module",
        ],
        order_by="doc_type, field_name",
    )

    # Aggregate property setters by doc_type and field grouping
    aggregated = {}
    for ps in property_setters:
        # Determine the fieldname key for aggregation
        if ps["doctype_or_field"] == "DocType":
            fieldname = ps["doc_type"]
        elif ps["doctype_or_field"] == "DocField":
            fieldname = f"{ps['doc_type']} / {ps['field_name']}"
        else:
            fieldname = (
                f"{ps['doc_type']} / {ps.get('field_name') or ps.get('row_name')}"
            )

        # Create aggregation key
        key = (ps["doc_type"], fieldname, ps["module"], ps["doctype_or_field"])

        if key not in aggregated:
            aggregated[key] = {
                "customization_type": "Property Setter",
                "dt": ps["doc_type"],
                "fieldname": fieldname,
                "properties": [],
                "module": ps["module"],
                "custom_field_name": None,
                "doctype_or_field": ps["doctype_or_field"],
            }

        aggregated[key]["properties"].append(f"{ps['property']}={ps['value']}")

    # Convert to list and format properties
    result = []
    for data in aggregated.values():
        # Sort properties and join with separator
        data["properties"] = "; ".join(sorted(data["properties"]))
        result.append(data)

    # Sort by doc_type and fieldname
    result.sort(key=lambda x: (x["dt"], x["fieldname"]))

    return result
