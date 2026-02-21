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

    return columns, data


def apply_where_query(columns, data, query):
    if not data:
        return data

    try:
        with make_queryable({"dataset": table_data}) as db:
            filtered = db.execute(
                f"SELECT * FROM dataset WHERE {query}",
                as_dict=True,
            )
    except Exception:
        frappe.throw(_("Invalid DuckDB WHERE query."))

    return filtered
