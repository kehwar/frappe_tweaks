import frappe
from frappe import _


def get_context(context):
    """
    Get context for rendering HTML file from File doctype.

    This handler is called by Frappe's website route system.
    The route parameter will be passed as part of frappe.form_dict or path.
    """
    # Get the file name from the route
    file_name = (
        frappe.form_dict.get("file_name") or frappe.local.request.path.split("/")[-1]
    )

    # Clean up the file name
    if file_name.startswith("html-file/"):
        file_name = file_name.replace("html-file/", "")

    # If no file name provided, show error
    if not file_name:
        frappe.throw("No file name provided")

    # Render the HTML file content
    html_content = render_html_file(file_name)

    # Return the raw HTML
    context.no_cache = 1
    context.html_content = html_content
    context.safe_render = False

    return context


def render_html_file(file_name):
    """
    Render HTML file from File doctype by name.

    Note: Authorization is handled by frappe.get_doc which checks permissions
    based on the File doctype's has_permission method.

    Args:
            file_name (str): Name of the file to search in File doctype

    Returns:
            str: HTML content of the file
    """
    # Search for the file in File doctype
    file_doc = frappe.db.get_value(
        "File",
        {"name": file_name},
        ["name", "file_url", "file_type"],
        as_dict=True,
    )

    if not file_doc:
        frappe.throw(
            _("HTML file '{0}' not found").format(file_name), frappe.DoesNotExistError
        )

    # Check if it's an HTML file
    if file_doc.file_type and "html" not in file_doc.file_type.lower():
        frappe.throw(_("File '{0}' is not an HTML file").format(file_name))

    # Get the full File document
    file = frappe.get_doc("File", file_doc.name)

    # Read the file content
    try:
        content = file.get_content()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        return content
    except Exception as e:
        frappe.log_error(f"Error reading HTML file {file_name}: {str(e)}")
        frappe.throw(_("Error reading HTML file '{0}'").format(file_name))
