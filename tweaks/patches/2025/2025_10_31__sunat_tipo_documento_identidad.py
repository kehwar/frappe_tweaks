import frappe

from tweaks.tweaks.doctype.sunat_tipo_documento_identidad.sunat_tipo_documento_identidad import (
    install,
    post_install,
)


def execute():

    install()
    post_install()
    patch_customers()


def patch_customers():

    if frappe.db.has_column("Customer", "custom_rut_type"):
        patch_rut_type()
    if frappe.db.has_column("Customer", "custom_tax_id_type"):
        patch_tax_id_type()


def patch_rut_type():

    ids = frappe.get_all("SUNAT Tipo Documento Identidad", pluck="name")

    customers = frappe.get_all(
        "Customer", fields=["name", "custom_rut_type"], as_list=1
    )
    for name, rut_type in customers:
        if not rut_type or rut_type not in ids:
            continue
        frappe.db.set_value(
            "Customer",
            name,
            "sunat_tipo_documento_identidad",
            rut_type,
            update_modified=False,
        )


def patch_tax_id_type():

    ids = frappe.get_all("SUNAT Tipo Documento Identidad", pluck="name")
    codes = frappe.get_all("Tax Id Type", fields=["name", "code"], as_list=1)
    code_map = {name: code for name, code in codes}

    customers = frappe.get_all(
        "Customer", fields=["name", "custom_tax_id_type"], as_list=1
    )
    for name, tax_id_type in customers:
        if not tax_id_type or tax_id_type not in code_map:
            continue
        code = code_map[tax_id_type]
        if code not in ids:
            continue
        frappe.db.set_value(
            "Customer",
            name,
            "sunat_tipo_documento_identidad",
            code,
            update_modified=False,
        )
