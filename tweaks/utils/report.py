import frappe
from frappe.core.doctype.report.report import get_report_module_dotted_path


def clean_reports_with_missing_modules():
    """
    Clean up standard reports with missing modules after migration.
    This prevents errors from reports that reference modules that no longer exist.
    Checks if the actual module files exist, similar to Report.execute_module().
    """
    # Get all standard reports
    reports = frappe.get_all(
        "Report",
        filters={"is_standard": "Yes", "report_type": "Script Report"},
        fields=["name", "module"],
    )

    deleted_count = 0
    for report in reports:
        # Skip reports without a module
        if not report.module:
            continue

        # Check if the actual module files exist
        try:
            # Try to get the module path like execute_module does
            method_name = (
                get_report_module_dotted_path(report.module, report.name) + ".execute"
            )
            # This will raise an error if the module file doesn't exist
            frappe.get_attr(method_name)
        except (ImportError, AttributeError, KeyError) as e:
            # Module files don't exist or module is not mapped
            try:
                frappe.delete_doc(
                    "Report", report.name, force=True, ignore_permissions=True
                )
                deleted_count += 1
                print(
                    f"Deleted report '{report.name}' (missing module files: {report.module})"
                )
            except Exception as delete_error:
                print(f"Failed to delete report '{report.name}': {str(delete_error)}")

    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} report(s) with missing modules")
