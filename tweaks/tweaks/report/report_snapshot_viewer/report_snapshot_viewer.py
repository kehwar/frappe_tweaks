# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import gzip
import json

import frappe
from frappe import _

from tweaks.utils.duckdb import make_queryable


def execute(filters=None):
    filters = frappe._dict(filters or {})

    snapshot_file = (filters.get("snapshot_file") or "").strip()
    snapshot_file_path = (filters.get("snapshot_file_path") or "").strip()
    file_reference = snapshot_file or snapshot_file_path

    if not file_reference:
        return [], []

    payload = load_report_file(file_reference)

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
        data = apply_where_query(data, query)

    if filters.get("column_header_mode", "fieldname").strip().lower() == "fieldname":
        for column in columns:
            if isinstance(column, dict) and "fieldname" in column:
                column["label"] = column["fieldname"]

    return columns, data


def load_report_file(file_or_docname):
    if isinstance(file_or_docname, str):
        file_doc = find_file(file_or_docname)
    else:
        file_doc = file_or_docname

    if not file_doc or getattr(file_doc, "doctype", None) != "File":
        frappe.throw(
            _("Please provide a valid File document, docname, file name, or file URL.")
        )

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

    if not isinstance(payload, dict):
        frappe.throw(_("Selected file must contain a valid report JSON object."))

    return payload


def find_file(file_reference):
    reference = (file_reference or "").strip()
    if not reference:
        return None

    for fieldname in ("name", "file_url", "file_name"):
        file_docname = frappe.db.exists("File", {fieldname: reference})
        if file_docname:
            return frappe.get_doc("File", file_docname)

    return None


def apply_where_query(data, query):
    if not data:
        return data

    try:
        with make_queryable({"dataset": data}) as db:
            filtered = db.execute(
                f"SELECT * FROM dataset WHERE {query}",
                as_dict=True,
            )
    except Exception as e:
        frappe.throw(_("Invalid DuckDB WHERE query: {0}").format(str(e)))

    return filtered
