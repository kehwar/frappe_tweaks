import frappe
from frappe import _
from frappe.desk.query_report import build_xlsx_data, format_fields, valid_report_name
from frappe.desk.utils import EXPORTED_REPORT_FOLDER_PATH


@frappe.whitelist()
def export_query(report_name, data):
    from frappe.desk.utils import provide_binary_file

    report_name, file_extension, content = _export_query(report_name, data)

    provide_binary_file(report_name, file_extension, content)


def _export_query(report_name, data):
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

    file_extension = "xlsx"
    content = make_xlsx(
        xlsx_data, "Query Report", column_widths=column_widths
    ).getvalue()

    return report_name, file_extension, content


@frappe.whitelist()
def export_query_in_background(
    report_name, data, send_email=True, send_notification=True, user=None
):

    if user:
        frappe.only_for("System Manager")
    else:
        user = frappe.session.user

    job = frappe.enqueue(
        "tweaks.utils.query_report.run_export_query_job",
        report_name=report_name,
        data=data,
        send_email=send_email,
        send_notification=send_notification,
        queue="long",
        now=frappe.flags.in_test,
    )

    return job.id


def get_user_email(user):
    return frappe.get_cached_value("User", user, "email")


def run_export_query_job(
    report_name, data, send_email=True, send_notification=True, user=None
):
    from rq import get_current_job

    report_name, file_extension, content = _export_query(report_name, data)
    jobid = get_current_job().id

    _file = create_report_file(
        report_name,
        file_extension,
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
