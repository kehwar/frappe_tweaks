# Copyright (c) 2026, Erick W.R. and contributors
# See license.txt

import io

import frappe
from frappe.tests.utils import FrappeTestCase

from tweaks.utils.typst_print import (
    _build_sys_inputs_phase1,
    _extract_source_from_html,
    _get_typst_source,
    get_print_format_template,
    pdf_generator,
)

MINIMAL_TYPST = "#set page(width: 100pt, height: 50pt)\nHello from Typst"


def _make_print_format(typst_type=True, html=MINIMAL_TYPST):
    """Return a mock Print Format doc-like object."""
    pf = frappe._dict(
        print_format_type="Typst" if typst_type else "Jinja",
        html=html,
        custom_format=1,
        pdf_generator="typst" if typst_type else "wkhtmltopdf",
    )
    return pf


class TestGetTypstSource(FrappeTestCase):
    def test_returns_html_field_content(self):
        pf = _make_print_format(html="  #strong[Hi]  ")
        self.assertEqual(_get_typst_source(pf), "#strong[Hi]")

    def test_returns_empty_string_when_html_blank(self):
        pf = _make_print_format(html="")
        self.assertEqual(_get_typst_source(pf), "")

    def test_returns_empty_string_when_html_none(self):
        pf = _make_print_format(html=None)
        self.assertEqual(_get_typst_source(pf), "")


class TestExtractSourceFromHtml(FrappeTestCase):
    def test_extracts_between_markers(self):
        html = "<!-- typst-source-start -->#let x = 1<!-- typst-source-end -->"
        self.assertEqual(_extract_source_from_html(html), "#let x = 1")

    def test_returns_none_when_no_markers(self):
        self.assertIsNone(_extract_source_from_html("<html><body>No markers</body></html>"))

    def test_extracts_multiline_source(self):
        source = "#set page()\n#strong[test]\n"
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"
        self.assertEqual(_extract_source_from_html(html), source)


class TestGetPrintFormatTemplate(FrappeTestCase):
    def test_returns_none_for_non_typst_format(self):
        pf = _make_print_format(typst_type=False)
        jenv = frappe.get_jenv()
        result = get_print_format_template(jenv=jenv, print_format=pf)
        self.assertIsNone(result)

    def test_returns_none_when_print_format_is_none(self):
        jenv = frappe.get_jenv()
        result = get_print_format_template(jenv=jenv, print_format=None)
        self.assertIsNone(result)

    def test_returns_template_for_typst_format(self):
        pf = _make_print_format()
        jenv = frappe.get_jenv()
        result = get_print_format_template(jenv=jenv, print_format=pf)
        self.assertIsNotNone(result)

    def test_rendered_template_contains_source_and_markers(self):
        pf = _make_print_format(html="#strong[Invoice]")
        jenv = frappe.get_jenv()
        template = get_print_format_template(jenv=jenv, print_format=pf)
        rendered = template.render({})
        self.assertIn("<!-- typst-source-start -->", rendered)
        self.assertIn("<!-- typst-source-end -->", rendered)
        self.assertIn("#strong[Invoice]", rendered)

    def test_jinja_does_not_process_typst_characters(self):
        """Typst '#' and '{}' must not be interpreted by Jinja."""
        pf = _make_print_format(html="#let x = { 1 + 2 }")
        jenv = frappe.get_jenv()
        template = get_print_format_template(jenv=jenv, print_format=pf)
        rendered = template.render({})
        self.assertIn("#let x = { 1 + 2 }", rendered)


class TestPdfGeneratorHook(FrappeTestCase):
    def test_returns_none_for_non_typst_generator(self):
        result = pdf_generator(
            print_format=None,
            html="<html>test</html>",
            options={},
            output=None,
            pdf_generator="wkhtmltopdf",
        )
        self.assertIsNone(result)

    def test_returns_pdf_bytes_for_minimal_typst(self):
        source = "#set page(width: 100pt, height: 50pt)\nHello"
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"

        result = pdf_generator(
            print_format=None,
            html=html,
            options={},
            output=None,
            pdf_generator="typst",
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        self.assertTrue(result.startswith(b"%PDF"), "Result must be a valid PDF")

    def test_appends_to_existing_pdf_writer(self):
        from pypdf import PdfWriter

        source = "#set page(width: 100pt, height: 50pt)\nPage 1"
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"
        writer = PdfWriter()

        result = pdf_generator(
            print_format=None,
            html=html,
            options={},
            output=writer,
            pdf_generator="typst",
        )

        self.assertIsInstance(result, PdfWriter)
        self.assertGreaterEqual(len(result.pages), 1)

    def test_throws_when_source_not_found(self):
        with self.assertRaises(frappe.exceptions.ValidationError):
            pdf_generator(
                print_format=None,
                html="<html>no markers here</html>",
                options={},
                output=None,
                pdf_generator="typst",
            )


class TestBuildSysInputsPhase1(FrappeTestCase):
    def test_all_values_are_strings(self):
        frappe.local.form_dict.update(
            {
                "doctype": "Sales Invoice",
                "name": "SINV-0001",
                "format": "My Format",
            }
        )
        inputs = _build_sys_inputs_phase1()
        for key, value in inputs.items():
            self.assertIsInstance(value, str, f"sys_inputs['{key}'] must be str")

    def test_contains_expected_keys(self):
        inputs = _build_sys_inputs_phase1()
        for key in ("doctype", "docname", "print_format_name", "language"):
            self.assertIn(key, inputs)
