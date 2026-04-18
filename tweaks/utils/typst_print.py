"""
Typst Print Format integration for Frappe.

Hooks:
  - get_print_format_template: wraps Typst source in {% raw %} so Jinja never
    processes '#', '{', '}' characters.  Returns a Jinja template whose
    rendered output is the original Typst source embedded in HTML comment
    markers ready for extraction by the pdf_generator hook.
  - pdf_generator: extracts the Typst source from the HTML comment markers,
    compiles it via TypstBuilder, and returns PDF bytes.

Phase 1 data context (minimal):
  sys_inputs only contains scalar metadata (doctype, docname, print_format_name,
  language).  Full doc/user/letterhead context is added in Phase 2.
"""

import re

import frappe

_SOURCE_START = "<!-- typst-source-start -->"
_SOURCE_END = "<!-- typst-source-end -->"


# ---------------------------------------------------------------------------
# Hook 1 — get_print_format_template
# ---------------------------------------------------------------------------


def get_print_format_template(jenv, print_format):
    """
    Called by frappe/www/printview.py before standard template rendering.

    Returns a Jinja template that embeds the Typst source verbatim inside
    HTML comment markers (bypassing Jinja processing via {% raw %}) when
    print_format_type == "Typst".  Returns None for all other formats so
    Frappe falls through to its default rendering.
    """
    if not print_format or getattr(print_format, "print_format_type", None) != "Typst":
        return None

    source = _get_typst_source(print_format)
    if not source:
        return None

    # Wrap source in {% raw %}...{% endraw %} so Jinja never interprets
    # '#', '{', '}' that appear in Typst markup.  Surround with comment
    # markers so the pdf_generator hook can extract the source from the
    # full printview HTML.
    wrapper = _SOURCE_START + "{% raw %}" + source + "{% endraw %}" + _SOURCE_END
    return jenv.from_string(wrapper)


# ---------------------------------------------------------------------------
# Hook 2 — pdf_generator
# ---------------------------------------------------------------------------


def pdf_generator(print_format, html, options, output, pdf_generator):
    """
    Called by frappe/utils/print_utils.py when pdf_generator != "wkhtmltopdf".

    Extracts Typst source from HTML comment markers, compiles via TypstBuilder,
    and returns PDF bytes.  Returns None if pdf_generator != "typst" so other
    hooks in the chain can handle it.

    When `output` (a pypdf.PdfWriter) is provided, compiled pages are appended
    to it and the writer is returned instead of raw bytes.
    """
    if pdf_generator != "typst":
        return None

    source = _extract_source_from_html(html)
    if not source:
        frappe.throw(
            frappe._("Typst source not found in print output."),
            title=frappe._("Typst Print Error"),
        )

    sys_inputs = _build_sys_inputs_phase1()

    from tweaks.utils.typst import TypstBuilder

    builder = TypstBuilder()
    builder.read_string(source)

    pdf_bytes = builder.compile(format="pdf", sys_inputs=sys_inputs)

    if output is not None:
        try:
            import io

            from pypdf import PdfReader, PdfWriter

            reader = PdfReader(io.BytesIO(pdf_bytes))
            if not isinstance(output, PdfWriter):
                output = PdfWriter()
            for page in reader.pages:
                output.add_page(page)
            return output
        except ImportError:
            pass  # pypdf not available — fall through and return raw bytes

    return pdf_bytes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_typst_source(print_format) -> str:
    """
    Phase 1: returns inline Typst markup from the print format's html field.
    Phase 3 will extend this to also check the module filesystem path for
    .typ / .tar.gz files before falling back to the html field.
    """
    return (print_format.html or "").strip()


def _extract_source_from_html(html: str) -> str | None:
    """Extract Typst source from the HTML comment markers."""
    pattern = re.compile(
        re.escape(_SOURCE_START) + r"(.*?)" + re.escape(_SOURCE_END),
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        return None
    return match.group(1)


def _build_sys_inputs_phase1() -> dict[str, str]:
    """
    Build minimal sys.inputs for Phase 1 (scalar metadata only).

    Typst sys.inputs only accepts str values.  Full doc/user/letterhead
    context (as virtual JSON files) is added in Phase 2.
    """
    form_dict = frappe.local.form_dict
    return {
        "doctype": str(form_dict.get("doctype") or ""),
        "docname": str(form_dict.get("name") or ""),
        "print_format_name": str(form_dict.get("format") or ""),
        "language": str(frappe.local.lang or ""),
    }
