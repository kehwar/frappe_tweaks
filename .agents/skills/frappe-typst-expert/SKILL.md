---
name: frappe-typst-expert
description: Expert guidance for generating PDF, PNG, and SVG documents from Typst markup in Frappe apps using the TypstBuilder helper. Use when compiling Typst templates, building documents from Frappe File records, passing dynamic data to templates, returning compiled output via HTTP, saving compiled files to Frappe File, or working with multi-file Typst projects (tar.gz archives).
---

# Frappe Typst Expert

`tweaks/utils/typst.py` wraps the `typst-py` Python package (`import typst`) with a Frappe-aware `TypstBuilder` class and convenience helpers. All compilation happens in-process—no CLI required.

## Module Location

```
tweaks/utils/typst.py
```

Exposed in `safe_exec` as `typst.build(...)`.

## `build()` — Convenience Entry Point

```python
from tweaks.utils.typst import build

builder = build(raw="...")        # from markup string or bytes
builder = build(doc="FILE-0001") # from Frappe File document name
builder = build(path="/srv/templates/invoice.typ")  # from filesystem path
builder = build(files={          # multi-file project
    "main.typ": b"...",
    "lib.typ": b"...",
})
```

Exactly one of `raw`, `doc`, `path`, or `files` must be provided. Returns a `TypstBuilder` instance.

## `TypstBuilder` — Full API

### Loading Files

```python
builder = TypstBuilder()

# From filesystem (.typ file or .tar.gz archive)
builder.read_file_path("template.typ")
builder.read_file_path("bundle.tar.gz")          # extracts all; needs main.typ
builder.read_file_path("template.typ", name="invoice")  # stored as "invoice.typ"

# From Frappe File document
builder.read_file_doc("FILE-000123")
builder.read_file_doc("FILE-000123", name="invoice")

# From string / bytes
builder.read_string("= Hello")
builder.read_string(markup_bytes, name="lib")

# From dict (multi-file project)
builder.read_files({
    "main.typ": b'#import "lib.typ": greet\n= Hello\n#greet("World")',
    "lib.typ": b'#let greet(name) = [Hello, #name!]',
})
```

All `read_*` methods return `self` for chaining. The `name` argument is normalized: if no extension is present, `.typ` is appended. Defaults to `"main.typ"`.

### Compiling

```python
# Returns bytes
pdf_bytes = builder.compile()                          # default: PDF
png_bytes = builder.compile(format="png", ppi=144.0)
svg_bytes = builder.compile(format="svg")

# With dynamic data (values must be strings)
pdf_bytes = builder.compile(
    sys_inputs={"invoice_no": "INV-001", "amount": "1000"}
)
```

`compile()` raises `frappe.ValidationError` on failure (via `frappe.throw`).

### Saving to Frappe File

```python
file_doc = builder.compile_and_save(
    "invoice.pdf",
    # format inferred from extension; override with format="pdf"
    ppi=144.0,                           # PNG only
    sys_inputs={"invoice_no": "INV-001"},
    attached_to_doctype="Sales Invoice",
    attached_to_name="INV-001",
    is_private=1,                        # default
    folder="Home",                       # default
)
# file_doc is a Frappe File document
```

### HTTP Response (Whitelisted Endpoints)

```python
@frappe.whitelist()
def generate_invoice(invoice_no):
    builder = build(doc="FILE-000123")
    builder.compile_response(
        format="pdf",
        sys_inputs={"invoice_no": invoice_no},
        filename=f"invoice_{invoice_no}.pdf",
        download=True,   # False = inline display
    )
```

Sets `frappe.response` fields: `filename`, `filecontent`, `content_type`, `type`.

### Saving Templates as tar.gz

```python
file_doc = builder.save_files_as_tar(
    "templates.tar.gz",
    attached_to_doctype="My DocType",
    attached_to_name="DOC-001",
    is_private=1,
    folder="Home",
)
```

Packs all files in `builder.files` into a gzipped tar archive and saves as a Frappe File.

### Querying Elements

```python
result = builder.query("<heading>", field="value", one=True)
# result is parsed from JSON by typst.query()
```

## `generate()` — Built-in HTTP Endpoint

Whitelisted method for serving compiled archives via URL:

```
/api/method/tweaks.utils.typst.generate?file=FILE-000123&format=pdf&download=1
```

```python
# From JavaScript
frappe.call({
    method: "tweaks.utils.typst.generate",
    args: {
        file: "FILE-000123",
        format: "pdf",
        sys_inputs: { name: "John", total: "1000" },
        download: 1,
    },
})
```

Parameters: `file` (File doc name, must be .tar.gz), `format` ("pdf"/"png"/"svg"), `ppi` (float), `sys_inputs` (dict or JSON string), `download` (truthy).

## Usage in `safe_exec` / Server Scripts

```python
# typst.build is available in safe_exec globals
builder = typst.build(doc="FILE-000123")
file_doc = builder.compile_and_save(
    "output.pdf",
    sys_inputs={"name": frappe.session.user},
)
```

## Passing Dynamic Data

`sys_inputs` values must be **strings**. Serialize complex types with `json.dumps`:

```python
import json
sys_inputs = {
    "items": json.dumps([{"name": "A", "qty": 2}]),
    "total": str(total),
}
```

In the Typst template, deserialize with `json(bytes(sys.inputs.items))`.

## Multi-file Projects (tar.gz)

The tar archive must contain `main.typ` (or `main`) as the entry point. Use `save_files_as_tar()` to create and store archives, then load them back with `read_file_doc()` or `read_file_path()`.

## Error Handling

All errors are raised via `frappe.throw()` which translates to `frappe.ValidationError`. Catch with:

```python
try:
    pdf = builder.compile()
except frappe.ValidationError as e:
    frappe.log_error(str(e))
```
