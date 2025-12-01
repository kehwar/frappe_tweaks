import os

import frappe
from frappe import _
from frappe.desk.query_report import build_xlsx_data, format_fields, get_report_doc, run

from tweaks.utils.groupby import group_aggregate
from tweaks.utils.preflight import get_preflight_css


@frappe.whitelist()
def export_query(
    report_name, extension, data=None, filters=None, file_name=None, pdf_generator=None
):

    content = get_export_content(
        report_name, extension, data, filters, pdf_generator=pdf_generator
    )

    provide_binary_file(file_name or report_name, extension, content)


def get_xlxs_report_content(report_name, data):
    from frappe.utils.xlsxutils import make_xlsx

    data = frappe._dict(data)

    if not data.columns:
        frappe.respond_as_web_page(
            _("No data to export"),
            _("You can try changing the filters of your report."),
        )
        return

    format_fields(data)
    xlsx_data, column_widths = build_xlsx_data(
        data, visible_idx=[], include_indentation=0
    )

    content = make_xlsx(
        xlsx_data, "Query Report", column_widths=column_widths
    ).getvalue()

    return content


def get_export_content(
    report_name, extension, data=None, filters=None, pdf_generator=None
):
    # If filters provided instead of data, run the report to get data
    if filters:
        run_data = run(
            report_name,
            filters=filters,
            ignore_prepared_report=1,
        )
        data = data or {}
        data.update(run_data)

    if not data:
        frappe.throw(_("Either 'data' or 'filters' must be provided"))

    if "group_by" in data and "aggregate_by" in data:
        # Perform grouping and aggregation
        data["grouped"] = group_aggregate(
            data["result"],
            data["group_by"],
            data["aggregate_by"],
        )

    if extension == "pdf":
        return get_pdf_report_content(report_name, data, pdf_generator=pdf_generator)
    else:
        return get_xlxs_report_content(report_name, data)


@frappe.whitelist()
def export_query_in_background(
    report_name,
    extension,
    data=None,
    filters=None,
    file_name=None,
    send_email=True,
    send_notification=True,
    user=None,
    pdf_generator=None,
):

    if user:
        frappe.only_for("System Manager")
    else:
        user = frappe.session.user

    job = frappe.enqueue(
        "tweaks.utils.query_report.run_export_query_job",
        report_name=report_name,
        extension=extension,
        data=data,
        filters=filters,
        file_name=file_name,
        send_email=send_email,
        send_notification=send_notification,
        queue="long",
        now=frappe.flags.in_test,
        pdf_generator=pdf_generator,
    )

    return job.id


def get_user_email(user):
    return frappe.get_cached_value("User", user, "email")


def run_export_query_job(
    report_name,
    extension,
    data=None,
    filters=None,
    file_name=None,
    send_email=True,
    send_notification=True,
    user=None,
    pdf_generator=None,
):
    from rq import get_current_job

    content = get_export_content(
        report_name, extension, data, filters, pdf_generator=pdf_generator
    )
    jobid = get_current_job().id

    _file = create_report_file(
        file_name or report_name,
        extension,
        content,
        attached_to_name=report_name,
        user=user,
    )
    external_url = frappe.utils.get_url(_file.file_url)
    file_retention_hours = (
        frappe.get_system_settings("delete_background_exported_reports_after") or 48
    )
    subject = _("Your exported report: {0}").format(report_name)
    message = _(
        "The report you requested has been generated.<br><br>"
        "Click here to download:<br>"
        "<a href='{0}'>{0}</a><br><br>"
        "This link will expire in {1} hours."
    ).format(external_url, file_retention_hours)

    if send_email:

        frappe.sendmail(
            recipients=[get_user_email(user)],
            subject=subject,
            message=message,
            now=True,
        )

    if send_notification:

        frappe.get_doc(
            {
                "doctype": "Notification Log",
                "subject": subject,
                "email_content": message,
                "for_user": user,
                "type": "Alert",
                "document_type": "File",
                "document_name": _file.name,
                "link": _file.file_url,
            }
        ).insert(ignore_permissions=True)

    frappe.publish_realtime(
        "export_query_file_ready",
        {
            "url": _file.file_url,
            "report_name": report_name,
            "jobid": jobid,
            "external_url": external_url,
        },
        after_commit=True,
        user=user,
    )


def create_report_file(
    report_name: str,
    file_extension: str,
    content: bytes,
    attached_to_name: str,
    user: str = None,
):
    from frappe.desk.utils import (
        EXPORTED_REPORT_FOLDER_PATH,
        create_exported_report_folder_if_not_exists,
    )

    create_exported_report_folder_if_not_exists()

    _file = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": f"{report_name}.{file_extension}",
            "attached_to_doctype": "Report",
            "attached_to_name": attached_to_name,
            "content": content,
            "is_private": 1,
            "folder": EXPORTED_REPORT_FOLDER_PATH,
        }
    )
    if user or frappe.session.user != "Guest":
        _file.owner = user or frappe.session.user
    _file.save(ignore_permissions=True)

    return _file


def get_pdf_report_content(report_name, data, pdf_generator=None):
    from frappe.utils.pdf import get_pdf as wkhtmltopdf_get_pdf
    from print_designer.pdf_generator.pdf import get_pdf as chrome_get_pdf

    meta = get_pdf_report_meta(report_name)
    context = {"data": data}
    if meta.get("before_print"):
        meta.get("before_print")(data)
    if meta.get("get_print_utils"):
        context.update(meta.get("get_print_utils")())
    context.update(
        {
            "preflight_css": get_preflight_css(),
        }
    )
    html = frappe.render_template(meta.get("html_format"), context)

    if pdf_generator == "chrome":
        content = chrome_get_pdf(
            print_format=report_name,
            html=html,
            options={},
            output=None,
            pdf_generator="chrome",
        )

    else:
        content = wkhtmltopdf_get_pdf(html)

    return content


def get_pdf_report_meta(report_name):
    from frappe.core.doctype.report.report import get_report_module_dotted_path
    from frappe.modules import get_module_path, scrub
    from frappe.utils import get_html_format

    report = get_report_doc(report_name)
    module = report.module or frappe.db.get_value(
        "DocType", report.ref_doctype, "module"
    )

    # Report HTML Format
    module_path = get_module_path(module)
    report_folder = module_path and os.path.join(
        module_path, "report", scrub(report.name)
    )
    print_path = report_folder and os.path.join(
        report_folder, scrub(report.name) + ".jinja"
    )
    html_format = get_html_format(print_path)

    # Report Module
    report_module_dotted_path = get_report_module_dotted_path(module, report_name)
    report_module = frappe.get_module(report_module_dotted_path)
    before_print = getattr(report_module, "before_print", "")
    get_print_utils = getattr(report_module, "get_print_utils", "")

    # Return
    return {
        "html_format": html_format,
        "before_print": before_print if callable(before_print) else None,
        "get_print_utils": get_print_utils if callable(get_print_utils) else None,
    }


def provide_binary_file(filename: str, extension: str, content: bytes) -> None:
    """Provide a binary file to the client."""
    from frappe import _

    frappe.response["type"] = "pdf" if extension == "pdf" else "binary"
    frappe.response["filecontent"] = content
    frappe.response["filename"] = f"{_(filename)}.{extension}"
