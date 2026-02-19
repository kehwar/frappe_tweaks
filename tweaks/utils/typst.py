"""
Typst utilities for frappe_tweaks

This module provides helper functions for working with Typst, a modern markup-based
typesetting system for creating PDFs.
"""

import re
import subprocess
import tempfile
from pathlib import Path

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

    # Create temporary files for input and output
    with tempfile.TemporaryDirectory() as tmpdir:
        typst_file = Path(tmpdir) / "input.typ"
        pdf_file = Path(tmpdir) / "output.pdf"

        # Write Typst content to temporary file
        typst_file.write_text(typst_content, encoding="utf-8")

        try:
            # Compile Typst to PDF
            subprocess.run(
                ["typst", "compile", str(typst_file), str(pdf_file)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
                timeout=30,
            )
        except subprocess.CalledProcessError as e:
            frappe.throw(
                f"Typst compilation failed: {e.stderr}",
                title="Typst Compilation Error",
            )
        except subprocess.TimeoutExpired:
            frappe.throw(
                "Typst compilation timed out (30 seconds)",
                title="Typst Compilation Timeout",
            )
        except FileNotFoundError:
            frappe.throw(
                "Typst executable not found. Please ensure Typst is installed.",
                title="Typst Not Found",
            )

        # Read the generated PDF
        with open(pdf_file, "rb") as f:
            pdf_content = f.read()

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
