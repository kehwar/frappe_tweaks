# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import json
from typing import Any, Dict, Optional

import frappe
import yaml
from frappe.model.document import Document

from tweaks.tweaks.doctype.peru_api_com.peru_api_com import (
    get_dni,
    get_ruc,
    get_ruc_suc,
    get_tc,
)


class PERUAPICOMConsole(Document):
    """
    Peru API Console Document class for testing Peru API services.

    This class extends Frappe's Document and provides a console interface
    for testing DNI, RUC, and exchange rate (TC) lookups through the Peru API.
    """

    pass


@frappe.whitelist()
def search(doc: str) -> Document:
    """
    Search for data using Peru API services based on search type.

    This function processes search requests for different Peru API services:
    - RUC: Search for company information by RUC number
    - DNI: Search for person information by DNI number
    - TC: Get exchange rate information

    Args:
        doc (str): JSON string representation of the document containing search parameters
                  Expected fields:
                  - search: Type of search ("RUC", "DNI", or "TC")
                  - search_ruc: RUC number to search (when search="RUC")
                  - search_dni: DNI number to search (when search="DNI")
                  - search_tc: Exchange rate parameters (when search="TC")
                  - ignore_cache: Boolean flag to bypass cache

    Returns:
        Document: Updated document with search results in 'data' field or error in 'error' field

    Raises:
        Exception: Any errors during API calls are caught and stored in doc.error
    """
    doc = frappe.get_doc(json.loads(doc))
    cache = not doc.ignore_cache

    doc.data = None
    doc.error = None

    try:
        if doc.search == "RUC" and doc.search_ruc:
            doc.data = get_ruc(doc.search_ruc.strip(), sucursales=True, cache=cache)
        elif doc.search == "RUC (Cabecera)" and doc.search_ruc:
            doc.data = get_ruc(doc.search_ruc.strip(), cache=cache)
        elif doc.search == "RUC (Sucursales)" and doc.search_ruc:
            doc.data = get_ruc_suc(doc.search_ruc.strip(), cache=cache)
        elif doc.search == "DNI" and doc.search_dni:
            doc.data = get_dni(doc.search_dni.strip(), cache=cache)
        elif doc.search == "TC":
            doc.data = get_tc(doc.search_tc, cache=cache)
        if doc.data:
            doc.data = json.dumps(doc.data, indent=4, ensure_ascii=True)
    except Exception:
        doc.error = frappe.get_traceback()

    return doc
