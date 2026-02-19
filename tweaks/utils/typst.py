"""
Typst utilities for frappe_tweaks

This module provides helper functions for working with Typst, a modern markup-based
typesetting system for creating PDFs.
"""

import typst
import frappe
from frappe.utils.file_manager import save_file


def make_pdf_file(
    typst_content, filename=None, doctype=None, docname=None, folder=None, is_private=1
):
    """
    Convert Typst markup to PDF and save as a Frappe File document.

    Args:
        typst_content (str): The Typst markup content to compile
        filename (str, optional): Name for the PDF file. If not provided, a temporary name is used
        doctype (str, optional): DocType to attach the file to
        docname (str, optional): Document name to attach the file to
        folder (str, optional): Folder to save the file in
        is_private (int, optional): Whether the file should be private (1) or public (0). Defaults to 1 (private)

    Returns:
        frappe.model.document.Document: The created File document

    Example:
        >>> typst_content = '''
        ... #set page(paper: "a4")
        ... #set text(font: "Linux Libertine", size: 11pt)
        ...
        ... = Hello World
        ...
        ... This is a *bold* statement.
        ... '''
        >>> file_doc = make_pdf_file(typst_content, filename="hello.pdf")
        >>> print(file_doc.file_url)
    """
    if not typst_content:
        frappe.throw("Typst content cannot be empty")

    # Generate a filename if not provided
    if not filename:
        filename = f"typst_output_{frappe.generate_hash(length=8)}.pdf"
    elif not filename.endswith(".pdf"):
        filename = f"{filename}.pdf"

    try:
        # Compile Typst to PDF using typst-py
        # Convert string to bytes if needed
        if isinstance(typst_content, str):
            typst_content_bytes = typst_content.encode("utf-8")
        else:
            typst_content_bytes = typst_content

        # Compile and get PDF bytes directly
        pdf_content = typst.compile(typst_content_bytes, format="pdf")

    except typst.TypstError as e:
        frappe.throw(
            f"Typst compilation failed: {str(e)}",
            title="Typst Compilation Error",
        )
    except Exception as e:
        frappe.throw(
            f"Unexpected error during Typst compilation: {str(e)}",
            title="Typst Error",
        )

    # Save as Frappe File document
    file_doc = save_file(
        filename,
        pdf_content,
        doctype,
        docname,
        folder=folder,
        is_private=is_private,
    )

    return frappe.get_doc("File", file_doc.name)
