# Copyright (c) 2025, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTypstUtils(FrappeTestCase):
    """Test cases for typst utility functions"""

    def test_make_pdf_file_basic(self):
        """Test basic PDF generation from Typst content"""
        typst_content = """
#set page(paper: "a4")
#set text(size: 11pt)

= Test Document

This is a *test* document.
"""
        file_doc = frappe.get_doc(
            "File",
            frappe.get_value(
                "File",
                {"file_name": "test_typst.pdf"},
                "name",
            )
            or frappe.new_doc("File").name,
        )

        # Import here to avoid import errors if typst is not installed
        from tweaks.utils.typst import make_pdf_file

        file_doc = make_pdf_file(typst_content, filename="test_typst.pdf")

        # Should return a File document
        self.assertIsInstance(file_doc, frappe.model.document.Document)
        self.assertEqual(file_doc.doctype, "File")

        # Should have a file_url
        self.assertTrue(file_doc.file_url)

        # Filename should end with .pdf
        self.assertTrue(file_doc.file_name.endswith(".pdf"))

        # Clean up
        frappe.delete_doc("File", file_doc.name)

    def test_make_pdf_file_empty_content(self):
        """Test that empty content throws an error"""
        from tweaks.utils.typst import make_pdf_file

        with self.assertRaises(frappe.ValidationError):
            make_pdf_file("")

    def test_make_pdf_file_with_filename(self):
        """Test PDF generation with a custom filename"""
        from tweaks.utils.typst import make_pdf_file

        typst_content = "= Custom Filename Test"

        file_doc = make_pdf_file(typst_content, filename="custom_name")

        # Filename should be custom_name.pdf
        self.assertEqual(file_doc.file_name, "custom_name.pdf")

        # Clean up
        frappe.delete_doc("File", file_doc.name)
