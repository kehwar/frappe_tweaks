# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# Fields compared when checking a Custom Field against the native tabDocField row.
_CF_COMPARE_FIELDS = frozenset(
    {
        "fieldtype",
        "label",
        "options",
        "default",
        "description",
        "depends_on",
        "mandatory_depends_on",
        "read_only_depends_on",
        "reqd",
        "hidden",
        "bold",
        "in_list_view",
        "in_standard_filter",
        "read_only",
        "allow_on_submit",
        "search_index",
        "no_copy",
        "print_hide",
        "print_hide_if_no_value",
        "fetch_from",
        "fetch_if_empty",
        "permlevel",
        "precision",
        "length",
        "columns",
        "translatable",
        "unique",
    }
)

_CF_INT_FIELDS = frozenset(
    {
        "reqd",
        "hidden",
        "bold",
        "in_list_view",
        "in_standard_filter",
        "read_only",
        "allow_on_submit",
        "search_index",
        "no_copy",
        "print_hide",
        "print_hide_if_no_value",
        "fetch_if_empty",
        "permlevel",
        "length",
        "columns",
        "translatable",
        "unique",
    }
)


def _norm(val, is_int):
    """Normalize a value for comparison: absent/None treated as 0 (int) or '' (str)."""
    if is_int:
        if val is None or val == "":
            return 0
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0
    return val or ""


def _cf_status(cf_props, native_field_row):
    """
    Compute Active / Stale for a Custom Field against a tabDocField row.

    Active = the field doesn't exist natively, or at least one compared property differs.
    Stale  = the field exists natively and every compared property matches exactly.
    """
    if native_field_row is None:
        return "Active"
    for prop in _CF_COMPARE_FIELDS:
        is_int = prop in _CF_INT_FIELDS
        if _norm(cf_props.get(prop), is_int) != _norm(
            native_field_row.get(prop), is_int
        ):
            return "Active"
    return "Stale"


# Properties that cannot be legally applied to standard DocTypes (Frappe rejects them
# during migration). Always reported as Active so they remain visible but are never
# incorrectly flagged as Stale.
_ALWAYS_ACTIVE_PROPERTIES = frozenset({"default_print_format"})


def _ps_status(
    property_name,
    value,
    doctype_or_field,
    native_field_row,
    native_dt_row,
    field_exists=True,
):
    """
    Compute Active / Stale for a Property Setter.

    Compares against the live tabDocField (DocField PS) or tabDocType (DocType PS) row.
    Active = the PS overrides a different native value, or property has no DB column,
             or the property is in _ALWAYS_ACTIVE_PROPERTIES.
    Stale  = the PS value matches the native value exactly, OR the target field no
             longer exists (orphaned PS).
    """
    if property_name in _ALWAYS_ACTIVE_PROPERTIES:
        return "Active"

    if doctype_or_field == "DocType":
        # native_dt_row is None if property isn't a valid tabDocType column → Active
        if native_dt_row is None:
            return "Active"
        native_raw = native_dt_row.get(property_name)
    else:
        # If the referenced field doesn't exist at all (neither native nor custom),
        # the PS is orphaned and serves no purpose → Stale.
        if not field_exists:
            return "Stale"
        if native_field_row is None:
            return "Active"
        native_raw = native_field_row.get(property_name)

    # Use str(native_raw) when present so that integer 0 becomes "0", not "".
    # None means the column doesn't exist / was absent → treat as empty string.
    native_val = "" if native_raw is None else str(native_raw)
    ps_val = "" if value is None else str(value)
    return "Stale" if native_val == ps_val else "Active"


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
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100,
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
            "fieldname": "fieldtype",
            "label": _("Field Type"),
            "fieldtype": "Data",
            "width": 140,
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

    if not filters.get("show_system_generated"):
        columns.append(
            {
                "fieldname": "is_system_generated",
                "label": _("System Generated"),
                "fieldtype": "Check",
                "width": 140,
            }
        )

    if not filters.get("show_custom_doctype"):
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

    # Fetch custom doctypes — used for both filtering and annotation
    custom_dt_set = {
        d["name"]
        for d in frappe.get_all(
            "DocType",
            filters={"name": ["in", list(dt_module_map)], "custom": 1},
            fields=["name"],
        )
    }

    # --- Batch-fetch native DocField rows for all doctypes ---
    docfield_props_needed = set(_CF_COMPARE_FIELDS)
    for row in data:
        if (
            row.get("customization_type") == "Property Setter"
            and row.get("doctype_or_field") == "DocField"
            and row.get("property")
        ):
            docfield_props_needed.add(row["property"])

    native_docfield_map = {}  # (dt, fieldname) -> field_dict
    if unique_dts:
        df_rows = frappe.get_all(
            "DocField",
            filters={"parent": ["in", list(unique_dts)]},
            fields=list(docfield_props_needed | {"parent", "fieldname"}),
        )
        for df in df_rows:
            if df.get("fieldname"):
                native_docfield_map[(df["parent"], df["fieldname"])] = df

    # --- Batch-fetch existing Custom Field (dt, fieldname) pairs ---
    # Used to detect orphaned DocField Property Setters (field deleted from both
    # native schema and custom fields).
    custom_field_key_set: set[tuple[str, str]] = set()
    if unique_dts:
        cf_key_rows = frappe.get_all(
            "Custom Field",
            filters={"dt": ["in", list(unique_dts)]},
            fields=["dt", "fieldname"],
        )
        for cf in cf_key_rows:
            if cf.get("fieldname"):
                custom_field_key_set.add((cf["dt"], cf["fieldname"]))

    # --- Batch-fetch native DocType rows for DocType-level PSes ---
    # Only fetch properties that are actual tabDocType columns; others → Active.
    native_doctype_map = {}  # dt -> dt_dict
    if unique_dts:
        dt_ps_props = {
            row["property"]
            for row in data
            if row.get("customization_type") == "Property Setter"
            and row.get("doctype_or_field") == "DocType"
            and row.get("property")
        }
        if dt_ps_props:
            doctype_cols = set(frappe.db.get_table_columns("DocType"))
            valid_dt_ps_props = dt_ps_props & doctype_cols
            if valid_dt_ps_props:
                dt_rows = frappe.get_all(
                    "DocType",
                    filters={"name": ["in", list(unique_dts)]},
                    fields=list(valid_dt_ps_props | {"name"}),
                )
                native_doctype_map = {r["name"]: r for r in dt_rows}

    # Compute status for each row
    for row in data:
        dt = row["dt"]
        if row["customization_type"] == "Custom Field":
            cf_props = row.pop("_cf_props", {})
            native_field_row = native_docfield_map.get((dt, row.get("fieldname") or ""))
            row["status"] = _cf_status(cf_props, native_field_row)
        else:
            fieldname = row.get("fieldname") or ""
            native_field_row = (
                native_docfield_map.get((dt, fieldname)) if fieldname else None
            )
            native_dt_row = native_doctype_map.get(dt)
            # A DocField PS whose fieldname no longer exists anywhere is orphaned.
            field_exists = bool(
                row.get("doctype_or_field") == "DocType"
                or (
                    fieldname
                    and (
                        (dt, fieldname) in native_docfield_map
                        or (dt, fieldname) in custom_field_key_set
                    )
                )
            )
            row["status"] = _ps_status(
                row.get("property") or "",
                row.get("value") or "",
                row.get("doctype_or_field") or "",
                native_field_row,
                native_dt_row,
                field_exists=field_exists,
            )

    # Apply status filter
    if filters.get("status"):
        data = [row for row in data if row.get("status") == filters["status"]]

    # Filter and annotate custom doctype
    show_custom = filters.get("show_custom_doctype")
    if show_custom in ("Yes", "No"):
        want_custom = show_custom == "Yes"
        data = [row for row in data if (row["dt"] in custom_dt_set) == want_custom]
    for row in data:
        row["is_custom_doctype"] = 1 if row["dt"] in custom_dt_set else 0

    return data


def get_custom_fields(filters):
    """Get Custom Fields data, fetching all comparison fields for status computation."""
    filter_dict = {}

    if filters.get("doctype"):
        filter_dict["dt"] = filters.get("doctype")

    if filters.get("customization_module"):
        filter_dict["module"] = filters.get("customization_module")

    show_sys_gen = filters.get("show_system_generated")
    if show_sys_gen == "Yes":
        filter_dict["is_system_generated"] = 1
    elif show_sys_gen == "No":
        filter_dict["is_system_generated"] = 0

    fetch_fields = list(
        {"dt", "fieldname", "module", "name", "is_system_generated"}.union(
            _CF_COMPARE_FIELDS
        )
    )

    custom_fields = frappe.get_all(
        "Custom Field",
        filters=filter_dict,
        fields=fetch_fields,
        order_by="dt, fieldname",
    )

    result = []
    ui_field_types = ["Column Break", "Section Break", "Tab Break"]
    show_ui = filters.get("show_ui_fields")

    for field in custom_fields:
        if show_ui == "No" and field.get("fieldtype") in ui_field_types:
            continue
        if show_ui == "Yes" and field.get("fieldtype") not in ui_field_types:
            continue

        result.append(
            {
                "dt": field["dt"],
                "fieldname": field.get("fieldname") or "",
                "fieldtype": field.get("fieldtype") or "",
                "customization_type": "Custom Field",
                "doctype_or_field": "DocField",
                "property": "",
                "value": "",
                "customization_module": field.get("module"),
                "customization_name": field["name"],
                "is_system_generated": field.get("is_system_generated", 0),
                "_cf_props": {prop: field.get(prop) for prop in _CF_COMPARE_FIELDS},
            }
        )

    return result


def get_property_setters(filters):
    """Get Property Setters data, one row per property setter"""
    filter_dict = {}

    if filters.get("doctype"):
        filter_dict["doc_type"] = filters.get("doctype")

    if filters.get("customization_module"):
        filter_dict["module"] = filters.get("customization_module")

    show_sys_gen = filters.get("show_system_generated")
    if show_sys_gen == "Yes":
        filter_dict["is_system_generated"] = 1
    elif show_sys_gen == "No":
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
