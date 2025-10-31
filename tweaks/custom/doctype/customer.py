import frappe
from frappe.utils import get_url_to_form

# Constants
SUNAT_DOCUMENT_TYPES = {"RUC": "6", "DNI": "1", "OTHER": "0"}


def _get_document_type_by_length(tax_id):
    """Determine SUNAT document type based on tax_id length"""
    if not tax_id or not isinstance(tax_id, str):
        return SUNAT_DOCUMENT_TYPES["OTHER"]

    length = len(tax_id.strip())
    if length == 11:
        return SUNAT_DOCUMENT_TYPES["RUC"]
    elif length == 8:
        return SUNAT_DOCUMENT_TYPES["DNI"]
    else:
        return SUNAT_DOCUMENT_TYPES["OTHER"]


def before_validate(doc, method=None):
    """Auto-assign SUNAT document type if not set"""
    if not doc.sunat_tipo_documento_identidad and doc.tax_id:
        doc.sunat_tipo_documento_identidad = _get_document_type_by_length(doc.tax_id)


def validate(doc, method=None):
    """Validate tax_id format and uniqueness"""
    if not doc.tax_id:
        return

    tax_id = doc.tax_id.strip()

    # Validate length based on document type
    if doc.sunat_tipo_documento_identidad == SUNAT_DOCUMENT_TYPES["RUC"]:
        if len(tax_id) != 11:
            frappe.throw("El RUC debe tener 11 dígitos.")
    elif doc.sunat_tipo_documento_identidad == SUNAT_DOCUMENT_TYPES["DNI"]:
        if len(tax_id) != 8:
            frappe.throw("El DNI debe tener 8 dígitos.")

    # Check for duplicates
    existing_name = frappe.db.get_value(
        "Customer",
        {
            "tax_id": tax_id,
            "sunat_tipo_documento_identidad": doc.sunat_tipo_documento_identidad,
            "name": ["!=", doc.name],
        },
    )

    if existing_name:
        url = get_url_to_form("Customer", existing_name)
        link_to = f"<a href='{url}' target='_blank'>{existing_name}</a>"
        frappe.throw(f"Ya existe un cliente con este Nro de Documento: <br>{link_to}")
