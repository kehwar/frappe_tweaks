"""
Typst Print Format integration for Frappe.

Hooks:
  - get_print_format_template: wraps Typst source in {% raw %} so Jinja never
    processes '#', '{', '}' characters.  Returns a Jinja template whose
    rendered output is the original Typst source embedded in HTML comment
    markers ready for extraction by the pdf_generator hook.
  - pdf_generator: extracts the Typst source from the HTML comment markers,
    builds the full data context via build_typst_context(), compiles via
    TypstBuilder, and returns PDF bytes.

Data context (Phase 2):
  sys_inputs carries str-only scalar metadata.  Structured data is injected
  as virtual JSON files (doc.json, user.json, letterhead.json) via
  builder.files so templates can access full document and session data.
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

    Extracts Typst source from HTML comment markers, builds the full data
    context, compiles via TypstBuilder, and returns PDF bytes.  Returns None
    if pdf_generator != "typst" so other hooks in the chain can handle it.

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

    form_dict = frappe.local.form_dict
    doctype = form_dict.get("doctype")
    docname = form_dict.get("name")
    no_letterhead = frappe.utils.cint(form_dict.get("no_letterhead", 0))
    letterhead_name = form_dict.get("letterhead") or None

    doc = None
    if doctype and docname:
        try:
            doc = frappe.get_doc(doctype, docname)
        except frappe.DoesNotExistError:
            pass
    sys_inputs, extra_files = build_typst_context(
        doc=doc,
        letter_head=letterhead_name,
        no_letterhead=no_letterhead,
    )

    from tweaks.utils.typst import TypstBuilder

    builder = TypstBuilder()
    builder.read_string(source)
    builder.files.update(extra_files)

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
# Public API: build_typst_context
# ---------------------------------------------------------------------------


def build_typst_context(
    doc=None,
    letter_head: str | None = None,
    no_letterhead: bool | int = False,
) -> tuple[dict[str, str], dict[str, bytes]]:
    """
    Build the complete Typst data context for a print job.

    Returns:
        sys_inputs: dict[str, str] — scalar metadata for Typst sys.inputs.
            Keys: doctype, docname, print_format_name, language, and
            letterhead scalar fields (lh_name, lh_company, lh_logo_url).
        extra_files: dict[str, bytes] — virtual JSON files to inject into
            builder.files before compilation.
            - doc.json: full document as dict (frappe.as_json serialised)
            - user.json: current session user (name, full_name, email, roles)
            - letterhead.json: letterhead fields, or {} when no_letterhead

    Templates access context as:
        #let doc = json("doc.json")
        #let user = json("user.json")
        #let lh = json("letterhead.json")
        sys.inputs.doctype, sys.inputs.language, etc.
    """
    form_dict = frappe.local.form_dict

    # --- doc.json ---
    if doc is not None:
        doc_dict = doc.as_dict()
    else:
        # Minimal stub so templates that reference doc.json don't crash
        doc_dict = {
            "name": str(form_dict.get("name") or ""),
            "doctype": str(form_dict.get("doctype") or ""),
        }

    # --- user.json ---
    user_name = frappe.session.user
    user_doc = frappe.get_cached_doc("User", user_name)
    user_data = {
        "name": user_doc.name,
        "full_name": user_doc.full_name or "",
        "email": user_doc.email or "",
        "roles": [r.role for r in (user_doc.roles or [])],
    }

    # --- letterhead.json ---
    lh_data: dict = {}
    lh_name = ""
    lh_company = ""
    lh_logo_url = ""

    if not no_letterhead and letter_head:
        try:
            lh_doc = frappe.get_cached_doc("Letter Head", letter_head)
            lh_data = {
                "name": lh_doc.name,
                "html": lh_doc.content or "",
                "footer": lh_doc.footer or "",
                "company": lh_doc.company or "",
                "logo_url": lh_doc.image or "",
            }
            lh_name = lh_doc.name
            lh_company = lh_doc.company or ""
            lh_logo_url = lh_doc.image or ""
        except frappe.DoesNotExistError:
            pass

    # --- sys_inputs (str values only) ---
    sys_inputs: dict[str, str] = {
        "doctype": str((doc.doctype if doc else form_dict.get("doctype")) or ""),
        "docname": str((doc.name if doc else form_dict.get("name")) or ""),
        "print_format_name": str(form_dict.get("format") or ""),
        "language": str(frappe.local.lang or ""),
        "lh_name": lh_name,
        "lh_company": lh_company,
        "lh_logo_url": lh_logo_url,
    }

    # --- extra_files ---
    extra_files: dict[str, bytes] = {
        "doc.json": frappe.as_json(doc_dict).encode("utf-8"),
        "user.json": frappe.as_json(user_data).encode("utf-8"),
        "letterhead.json": frappe.as_json(lh_data).encode("utf-8"),
    }

    return sys_inputs, extra_files


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
