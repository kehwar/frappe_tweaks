# Copyright (c) 2026, Erick W.R. and contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from tweaks.utils.typst_print import (
    _extract_source_from_html,
    _get_typst_source,
    build_typst_context,
    get_print_format_template,
    pdf_generator,
)

MINIMAL_TYPST = "#set page(width: 100pt, height: 50pt)\nHello from Typst"


def _make_print_format(typst_type=True, html=MINIMAL_TYPST):
    """Return a mock Print Format doc-like object."""
    return frappe._dict(
        print_format_type="Typst" if typst_type else "Jinja",
        html=html,
        custom_format=1,
        pdf_generator="typst" if typst_type else "wkhtmltopdf",
    )


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
        self.assertIsNone(get_print_format_template(jenv=jenv, print_format=pf))

    def test_returns_none_when_print_format_is_none(self):
        jenv = frappe.get_jenv()
        self.assertIsNone(get_print_format_template(jenv=jenv, print_format=None))

    def test_returns_template_for_typst_format(self):
        pf = _make_print_format()
        jenv = frappe.get_jenv()
        self.assertIsNotNone(get_print_format_template(jenv=jenv, print_format=pf))

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
    def setUp(self):
        super().setUp()
        # Isolate form_dict so stale doctype/name from other tests don't leak in
        frappe.local.form_dict.update({"doctype": "", "name": "", "format": ""})

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
            print_format=None, html=html, options={}, output=None, pdf_generator="typst"
        )
        self.assertIsInstance(result, bytes)
        self.assertTrue(result.startswith(b"%PDF"), "Result must be a valid PDF")

    def test_appends_to_existing_pdf_writer(self):
        from pypdf import PdfWriter

        source = "#set page(width: 100pt, height: 50pt)\nPage 1"
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"
        result = pdf_generator(
            print_format=None,
            html=html,
            options={},
            output=PdfWriter(),
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


class TestBuildTypstContext(FrappeTestCase):
    def test_sys_inputs_all_values_are_strings(self):
        sys_inputs, _ = build_typst_context()
        for key, value in sys_inputs.items():
            self.assertIsInstance(value, str, f"sys_inputs['{key}'] must be str")

    def test_sys_inputs_contains_expected_keys(self):
        sys_inputs, _ = build_typst_context()
        for key in ("doctype", "docname", "print_format_name", "language", "lh_name", "lh_company", "lh_logo_url"):
            self.assertIn(key, sys_inputs)

    def test_extra_files_contains_required_json_files(self):
        _, extra_files = build_typst_context()
        for name in ("doc.json", "user.json", "letterhead.json"):
            self.assertIn(name, extra_files)
            self.assertIsInstance(extra_files[name], bytes)

    def test_doc_json_round_trips(self):
        _, extra_files = build_typst_context()
        parsed = json.loads(extra_files["doc.json"])
        self.assertIsInstance(parsed, dict)

    def test_user_json_has_required_fields(self):
        _, extra_files = build_typst_context()
        user = json.loads(extra_files["user.json"])
        for field in ("name", "full_name", "email", "roles"):
            self.assertIn(field, user)
        self.assertIsInstance(user["roles"], list)

    def test_letterhead_json_empty_when_no_letterhead(self):
        _, extra_files = build_typst_context(no_letterhead=True)
        lh = json.loads(extra_files["letterhead.json"])
        self.assertEqual(lh, {})

    def test_letterhead_sys_inputs_empty_when_no_letterhead(self):
        sys_inputs, _ = build_typst_context(no_letterhead=True)
        self.assertEqual(sys_inputs["lh_name"], "")
        self.assertEqual(sys_inputs["lh_company"], "")
        self.assertEqual(sys_inputs["lh_logo_url"], "")

    def test_doc_json_uses_doc_fields_when_doc_provided(self):
        doc = frappe.get_doc("Print Settings")
        sys_inputs, extra_files = build_typst_context(doc=doc)
        parsed = json.loads(extra_files["doc.json"])
        self.assertEqual(parsed.get("doctype"), "Print Settings")
        self.assertEqual(sys_inputs["doctype"], "Print Settings")

    def test_pdf_generator_hook_injects_doc_json(self):
        """End-to-end: template that reads doc.json compiles to valid PDF."""
        source = (
            '#set page(width: 120pt, height: 60pt)\n'
            '#let d = json("doc.json")\n'
            '#d.at("name", default: "")'
        )
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"
        result = pdf_generator(
            print_format=None, html=html, options={}, output=None, pdf_generator="typst"
        )
        self.assertTrue(result.startswith(b"%PDF"))

    def test_pdf_generator_hook_injects_user_json(self):
        """End-to-end: template that reads user.json compiles to valid PDF."""
        source = (
            '#set page(width: 120pt, height: 60pt)\n'
            '#let u = json("user.json")\n'
            '#u.at("name", default: "")'
        )
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"
        result = pdf_generator(
            print_format=None, html=html, options={}, output=None, pdf_generator="typst"
        )
        self.assertTrue(result.startswith(b"%PDF"))

    def test_multi_pdf_merge_page_count(self):
        """Two single-page Typst PDFs merged into one writer produce 2 pages."""
        from pypdf import PdfWriter

        source = "#set page(width: 100pt, height: 50pt)\nA"
        html = f"<!-- typst-source-start -->{source}<!-- typst-source-end -->"

        writer = PdfWriter()
        writer = pdf_generator(
            print_format=None, html=html, options={}, output=writer, pdf_generator="typst"
        )
        writer = pdf_generator(
            print_format=None, html=html, options={}, output=writer, pdf_generator="typst"
        )
        self.assertEqual(len(writer.pages), 2)
