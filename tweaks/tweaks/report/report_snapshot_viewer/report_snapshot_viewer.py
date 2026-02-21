# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import gzip
import json

import frappe
from frappe import _

from tweaks.utils.duckdb import make_queryable


def execute(filters=None):
    filters = frappe._dict(filters or {})

    if not filters.get("snapshot_file"):
        return [], []

    file_doc = frappe.get_doc("File", filters.get("snapshot_file"))
    if file_doc.is_folder:
        frappe.throw(_("Please select a file, not a folder."))

    content = file_doc.get_content()

    try:
        content = gzip.decompress(content)
    except OSError:
        pass

    try:
        payload = json.loads(content)
    except Exception:
        frappe.throw(_("Selected file does not contain valid JSON report data."))

    columns = payload.get("columns") or []
    data = payload.get("result")
    if data is None:
        data = payload.get("data") or []

    if not isinstance(columns, list) or not isinstance(data, list):
        frappe.throw(
            _("Selected file must contain 'columns' (list) and 'result'/'data' (list).")
        )

    query = (filters.get("query") or "").strip()
    if query:
        data = apply_where_query(columns, data, query)

    columns = apply_column_header_mode(columns, filters.get("column_header_mode"))

    return columns, data


def apply_column_header_mode(columns, mode):
    if not isinstance(columns, list):
        return columns

    normalized_mode = (mode or "Label").strip().lower()
    use_fieldname = normalized_mode == "fieldname"

    rendered_columns = []
    for column in columns:
        if not isinstance(column, dict):
            rendered_columns.append(column)
            continue

        rendered_column = dict(column)
        fieldname = rendered_column.get("fieldname")
        label = rendered_column.get("label")

        if use_fieldname and fieldname:
            rendered_column["label"] = fieldname
        elif not label and fieldname:
            rendered_column["label"] = fieldname

        rendered_columns.append(rendered_column)

    return rendered_columns


def apply_where_query(columns, data, query):
    if not data:
        return data

    try:
        with make_queryable({"dataset": data}) as db:
            filtered = db.execute(
                f"SELECT * FROM dataset WHERE {query}",
                as_dict=True,
            )
    except Exception as e:
        frappe.throw(_("Invalid DuckDB WHERE query."))

    return filtered
