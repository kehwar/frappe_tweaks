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
            "fieldname": "customization_type",
            "label": _("Customization Type"),
            "fieldtype": "Data",
            "width": 150,
        },
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
            "fieldname": "label",
            "label": _("Label"),
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "fieldname": "fieldtype",
            "label": _("Field Type"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "property_count",
            "label": _("Property Count"),
            "fieldtype": "Int",
            "width": 120,
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
            "fieldname": "is_system_generated",
            "label": _("System Generated"),
            "fieldtype": "Check",
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

    return data


def get_custom_fields(filters):
    """Get Custom Fields data"""
    conditions = []
    values = {}

    if filters.get("doctype"):
        conditions.append("dt = %(doctype)s")
        values["doctype"] = filters.get("doctype")

    if filters.get("module"):
        conditions.append("module = %(module)s")
        values["module"] = filters.get("module")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    custom_fields = frappe.db.sql(
        f"""
        SELECT 
            'Custom Field' as customization_type,
            dt,
            fieldname,
            label,
            fieldtype,
            NULL as property_count,
            NULL as properties,
            module,
            is_system_generated,
            name as custom_field_name
        FROM `tabCustom Field`
        {where_clause}
        ORDER BY dt, fieldname
    """,
        values,
        as_dict=1,
    )

    return custom_fields


def get_property_setters(filters):
    """Get Property Setters data, aggregated by DocType or DocType/Fieldname"""
    conditions = []
    values = {}

    if filters.get("doctype"):
        conditions.append("doc_type = %(doctype)s")
        values["doctype"] = filters.get("doctype")

    if filters.get("module"):
        conditions.append("module = %(module)s")
        values["module"] = filters.get("module")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get property setters aggregated by doc_type and field_name
    property_setters = frappe.db.sql(
        f"""
        SELECT 
            'Property Setter' as customization_type,
            doc_type as dt,
            CASE 
                WHEN doctype_or_field = 'DocType' THEN doc_type
                WHEN doctype_or_field = 'DocField' THEN CONCAT(doc_type, ' / ', field_name)
                ELSE CONCAT(doc_type, ' / ', COALESCE(field_name, row_name))
            END as fieldname,
            NULL as label,
            NULL as fieldtype,
            COUNT(*) as property_count,
            GROUP_CONCAT(
                CONCAT(property, '=', value) 
                ORDER BY property 
                SEPARATOR '; '
            ) as properties,
            module,
            MAX(is_system_generated) as is_system_generated,
            NULL as custom_field_name,
            doctype_or_field
        FROM `tabProperty Setter`
        {where_clause}
        GROUP BY 
            doc_type,
            CASE 
                WHEN doctype_or_field = 'DocType' THEN doc_type
                WHEN doctype_or_field = 'DocField' THEN CONCAT(doc_type, ' / ', field_name)
                ELSE CONCAT(doc_type, ' / ', COALESCE(field_name, row_name))
            END,
            module,
            doctype_or_field
        ORDER BY doc_type, fieldname
    """,
        values,
        as_dict=1,
    )

    return property_setters
