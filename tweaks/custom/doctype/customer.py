import frappe
from frappe import _
from frappe.contacts.doctype.address.address import Address, get_address_display
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


def on_update(doc, method=None):
    """Create primary address from quick_primary_address field"""
    if hasattr(doc, "quick_primary_address") and doc.quick_primary_address:
        create_primary_address(doc)


def create_primary_address(doc):
    address_args = doc.quick_primary_address
    address_args.update({"doctype": "Customer", "name": doc.name})

    address = make_address(
        address_args, is_primary_address=1, is_shipping_address=1, insert=1
    )
    address_display = get_address_display(address.name)

    doc.db_set("customer_primary_address", address.name)
    doc.db_set("primary_address", address_display)


def make_address(args, is_primary_address=1, is_shipping_address=1, insert=1):
    """
    Create an address record linked to a document.

    Parameters:
        args (dict): Dictionary containing address and link details.
        is_primary_address (int): Flag to mark the address as primary.
        is_shipping_address (int): Flag to mark the address as a shipping address.
        insert (int): Flag to execute the insertion.
    """
    reqd_fields = []
    # Check for mandatory fields
    for field in ["city", "country"]:
        if not args.get(field):
            reqd_fields.append("<li>" + field.title() + "</li>")

    if reqd_fields:
        msg = _("Following fields are mandatory to create address:")
        frappe.throw(
            "{} <br><br> <ul>{}</ul>".format(msg, "\n".join(reqd_fields)),
            title=_("Missing Values Required"),
        )

    # Create and insert the address document
    address: Address = frappe.get_doc(
        {
            "doctype": "Address",
            "address_line1": args.get("address_line1"),
            "address_line2": args.get("address_line2"),
            "county": args.get("county"),
            "city": args.get("city"),
            "state": args.get("state"),
            "pincode": args.get("pincode"),
            "country": args.get("country"),
            "is_primary_address": is_primary_address,
            "is_shipping_address": is_shipping_address,
            "links": [
                {"link_doctype": args.get("doctype"), "link_name": args.get("name")}
            ],
        }
    )

    if insert:
        if flags := args.get("flags"):
            address.insert(ignore_permissions=flags.get("ignore_permissions"))
        else:
            address.insert()

    return address
