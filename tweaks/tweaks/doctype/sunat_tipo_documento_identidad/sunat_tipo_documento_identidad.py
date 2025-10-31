# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SUNATTipoDocumentoIdentidad(Document):

    pass


def post_install():

    defaults = [
        ["0", "OTRO", "DOC TRIB NO DOM SIN RUC"],
        ["1", "DNI", "DOCUMENTO NACIONAL DE IDENTIDAD"],
        ["4", "CE", "CARNET DE EXTRANJERIA"],
        ["6", "RUC", "REGISTRO UNICO DE CONTRIBUYENTES"],
        ["7", "PAS", "PASAPORTE"],
        ["A", "CDI", "CEDULA DIPLOMATICA DE IDENTIDAD"],
        ["B", "DIR", "DOCUMENTO IDENTIDAD PAIS DE RESIDENCIA"],
        ["C", "TIN", "TAX IDENTIFICATION NUMBER DOC TRIB PPNN"],
        ["D", "IN", "IDENTIFICATION NUMBER DOC TRIB PPJJ"],
        ["E", "TAM", "TARJETA ANDINA DE MIGRACION"],
        ["F", "PTP", "PERMISO TEMPORAL DE PERMANENCIA"],
    ]

    for code, abbr, description in defaults:

        if frappe.db.exists("SUNAT Tipo Documento Identidad", code):
            continue

        doc = frappe.get_doc(
            {
                "doctype": "SUNAT Tipo Documento Identidad",
                "name": code,
                "abbr": abbr,
                "description": description,
            }
        )
        doc.insert(ignore_permissions=True)


def install():

    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    fieldname = "sunat_tipo_documento_identidad"
    if not frappe.db.has_column("Customer", fieldname):
        create_custom_fields(
            {
                "Customer": [
                    {
                        "fieldname": fieldname,
                        "label": "Tipo Documento Identidad (SUNAT)",
                        "fieldtype": "Link",
                        "options": "SUNAT Tipo Documento Identidad",
                        "insert_after": "tax_id",
                    }
                ]
            }
        )
