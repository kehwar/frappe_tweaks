import frappe
from frappe import _
from frappe.core.doctype.prepared_report.prepared_report import make_prepared_report
from frappe.desk.query_report import get_prepared_report_result


@frappe.whitelist()
def start_job(report_name, **kwargs):
    """
    Create a new prepared report job using Frappe's native make_prepared_report API.

    Args:
        report_name: Name of the report to execute
        **kwargs: Filters for the report

    Returns:
        str: The prepared report name (job_id)
    """
    # Remove 'cmd' from kwargs if present (automatically added by frappe.call)
    kwargs.pop("cmd", None)

    # Use Frappe's native make_prepared_report function
    result = make_prepared_report(report_name=report_name, filters=kwargs)

    return result.get("name")


@frappe.whitelist()
def check_status(job_id):
    """
    Check the status of a prepared report job.

    Args:
        job_id: The prepared report name

    Returns:
        dict: Status information with 'status' field ("Queued", "Started", "Completed", "Error")
              Returns empty dict if job not found
    """
    try:
        prepared_report = frappe.get_doc("Prepared Report", job_id)
        return 1 if prepared_report.status in ("Completed", "Error") else 0
    except frappe.DoesNotExistError:
        return 1


@frappe.whitelist()
def get_result(job_id):
    """
    Get the result of a completed prepared report job.

    Args:
        job_id: The prepared report name

    Returns:
        dict: Report result if completed, empty dict if error or not found,
              or {'job_status': 'pending'} if still processing
    """
    try:
        prepared_report = frappe.get_doc("Prepared Report", job_id)

        # Check status
        if prepared_report.status == "Error":
            return {
                "columns": [],
                "result": [],
                "message": _("An error occurred while generating the report."),
            }

        if prepared_report.status == "Completed":
            # Use Frappe's native function to get the prepared report result
            result = get_prepared_report_result(None, None, dn=prepared_report.name)

            return result

        return {
            "columns": [],
            "result": [],
            "message": _("Report is still being generated."),
        }

    except frappe.DoesNotExistError:
        # Job not found
        return {
            "columns": [],
            "result": [],
            "message": _("Prepared report job not found."),
        }
