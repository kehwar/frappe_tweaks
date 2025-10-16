# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import json

import frappe
import yaml
from frappe.model.document import Document

from tweaks.tweaks.doctype.peru_api_com.peru_api_com import get_dni, get_ruc, get_tc


class PERUAPICOMConsole(Document):
    pass


@frappe.whitelist()
def search(doc):

    doc = frappe.get_doc(json.loads(doc))
    cache = not doc.ignore_cache

    doc.data = None
    doc.error = None

    try:
        if doc.search == "RUC" and doc.search_ruc:
            doc.data = get_ruc(doc.search_ruc.strip(), cache=cache)
        elif doc.search == "DNI" and doc.search_dni:
            doc.data = get_dni(doc.search_dni.strip(), cache=cache)
        elif doc.search == "TC":
            doc.data = get_tc(doc.search_tc, cache=cache)
        if doc.data:
            doc.data = json.dumps(doc.data, indent=4, ensure_ascii=True)
    except Exception:
        doc.error = frappe.get_traceback()

    return doc
