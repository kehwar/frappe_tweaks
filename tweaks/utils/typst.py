"""
Typst utilities for compiling Typst markup to PDF/PNG/SVG.

This module provides helpers to work with Typst, a markup-based typesetting system.

The TypstBuilder class allows you to:
- Load files from file paths, Frappe File documents, or strings
- Support multi-file projects with multiple files
- Compile to PDF, PNG, or SVG formats
- Save compiled output as Frappe File documents
- Pass dynamic values to templates
"""

import json
import os
from pathlib import Path
from typing import Any, Literal, Optional, Union

import frappe
import typst


class TypstBuilder:
    """
    Helper class to compile Typst files and save as Frappe Files.

    Supports loading files from file paths, Frappe File documents, or strings,
    and compiling to PDF, PNG, or SVG formats. Files are stored internally
    as a dict mapping filenames to bytes content.

    Usage:
        # From file path
        builder = TypstBuilder()
        builder.read_file_path("template.typ")
        builder.save("output.pdf")

        # From Frappe File document
        builder = TypstBuilder()
        builder.read_file_doc("FILE-000123")
        builder.save("output.pdf")

        # From string
        markup = "#set page(width: 10cm, height: auto)\\n= Hello World!"
        builder = TypstBuilder()
        builder.read_string(markup)
        builder.save("output.pdf")

        # With dynamic values and custom template names
        builder = TypstBuilder()
        builder.read_file_path("invoice.typ", name="invoice")
        builder.read_file_path("lib.typ", name="lib")
        builder.save(
            "invoice.pdf",
            sys_inputs={"invoice_no": "INV-001", "amount": "1000"}
        )
    """

    files: dict[str, bytes]  # Internal storage: filename -> bytes content

    def __init__(self):
        """
        Initialize TypstBuilder with empty files.

        Use read_* methods to add files.
        """
        self.files = {}
        self.compiler = typst.Compiler()

    def _normalize_name(self, name: Optional[str]) -> str:
        """
        Normalize file name, adding .typ extension if no extension present.

        Args:
            name: File name or None (defaults to "main.typ")

        Returns:
            Normalized name with extension
        """
        if name is None:
            return "main.typ"

        # Check if name has any extension
        _, ext = os.path.splitext(name)
        if not ext:
            # No extension present, add .typ
            return f"{name}.typ"

        return name

    def read_file_path(
        self, file_path: Union[str, Path], name: Optional[str] = None
    ) -> "TypstBuilder":
        """
        Read a .typ file from filesystem path and add to files.

        Args:
            file_path: Path to .typ file
            name: File name (defaults to "main.typ"). Will be normalized to include extension if missing.

        Returns:
            Self for method chaining
        """
        file_path = Path(file_path)
        if not file_path.exists():
            frappe.throw(f"File not found: {file_path}")

        if not file_path.suffix == ".typ":
            frappe.throw(f"File must have .typ extension: {file_path}")

        with open(file_path, "rb") as f:
            content = f.read()

        key = self._normalize_name(name)
        self.files[key] = content
        return self

    def read_file_doc(
        self, file_name: str, name: Optional[str] = None
    ) -> "TypstBuilder":
        """
        Read a Frappe File document and add to files.

        Args:
            file_name: Name of Frappe File document (e.g., "FILE-000123")
            name: File name (defaults to "main.typ"). Will be normalized to include extension if missing.

        Returns:
            Self for method chaining
        """
        if not frappe.db.exists("File", file_name):
            frappe.throw(f"File not found: {file_name}")

        file_doc = frappe.get_doc("File", file_name)

        # Check if it's a .typ file
        if not file_doc.file_name.endswith(".typ"):
            frappe.throw(f"File must have .typ extension: {file_doc.file_name}")

        # Get file content
        file_path = file_doc.get_full_path()
        with open(file_path, "rb") as f:
            content = f.read()

        key = self._normalize_name(name)
        self.files[key] = content
        return self

    def read_string(
        self, markup: Union[str, bytes], name: Optional[str] = None
    ) -> "TypstBuilder":
        """
        Read markup string and add to files.

        Args:
            markup: Typst markup as string or bytes
            name: File name (defaults to "main.typ"). Will be normalized to include extension if missing.

        Returns:
            Self for method chaining
        """
        if isinstance(markup, str):
            content = markup.encode("utf-8")
        else:
            content = markup

        key = self._normalize_name(name)
        self.files[key] = content
        return self

    def read_files(self, files: dict[str, Union[str, bytes, Path]]) -> "TypstBuilder":
        """
        Set multiple files at once from a dict.

        Args:
            files: Dict mapping filenames to content (str/bytes) or file paths
                  Entry point should be keyed as "main" or "main.typ"
                  Example:
                  {
                      "main.typ": b'#import "lib.typ": greet\\n= Hello\\n#greet("World")',
                      "lib.typ": b'#let greet(name) = [Hello, #name!]'
                  }

        Returns:
            Self for method chaining
        """
        if "main" not in files and "main.typ" not in files:
            frappe.throw(
                "Multi-file project must have 'main' or 'main.typ' entry point"
            )

        # Normalize all values to bytes
        normalized_dict = {}
        for key, value in files.items():
            if isinstance(value, str):
                normalized_dict[key] = value.encode("utf-8")
            elif isinstance(value, Path):
                with open(value, "rb") as f:
                    normalized_dict[key] = f.read()
            else:
                normalized_dict[key] = value

        self.files = normalized_dict
        return self

    def compile(
        self,
        format: Literal["pdf", "png", "svg"] = "pdf",
        ppi: Optional[float] = None,
        sys_inputs: Optional[dict[str, str]] = None,
    ) -> bytes:
        """
        Compile Typst files to specified format.

        Args:
            format: Output format - "pdf", "png", or "svg" (default: "pdf")
            ppi: Pixels per inch for PNG output (default: None)
            sys_inputs: Dictionary of values to pass to template
                       Values should be JSON-serializable strings
                       Example: {"name": "John", "items": json.dumps([...])}

        Returns:
            Compiled output as bytes
        """
        compile_kwargs = {
            "input": self.files,
            "format": format,
        }

        if ppi is not None and format == "png":
            compile_kwargs["ppi"] = ppi

        if sys_inputs:
            compile_kwargs["sys_inputs"] = sys_inputs

        try:
            return self.compiler.compile(**compile_kwargs)
        except Exception as e:
            frappe.throw(f"Typst compilation failed: {str(e)}")

    def save(
        self,
        output_filename: str,
        format: Optional[Literal["pdf", "png", "svg"]] = None,
        ppi: Optional[float] = None,
        sys_inputs: Optional[dict[str, str]] = None,
        attached_to_doctype: Optional[str] = None,
        attached_to_name: Optional[str] = None,
        is_private: int = 1,
        folder: str = "Home",
    ) -> "frappe._dict":
        """
        Compile Typst files and save as Frappe File document.

        Args:
            output_filename: Name for the output file (e.g., "invoice.pdf")
            format: Output format - "pdf", "png", or "svg"
                   If None, inferred from output_filename extension
            ppi: Pixels per inch for PNG output (default: None)
            sys_inputs: Dictionary of values to pass to template
            attached_to_doctype: Attach file to this DocType
            attached_to_name: Attach file to this document
            is_private: 1 for private file, 0 for public (default: 1)
            folder: Folder to save file in (default: "Home")

        Returns:
            Frappe File document
        """
        # Infer format from filename extension if not provided
        if format is None:
            ext = os.path.splitext(output_filename)[1].lower().lstrip(".")
            if ext not in ["pdf", "png", "svg"]:
                frappe.throw(
                    f"Cannot infer format from extension: {ext}. "
                    "Please specify format parameter."
                )
            format = ext  # type: ignore

        # Compile markup
        compiled_bytes = self.compile(format=format, ppi=ppi, sys_inputs=sys_inputs)

        # Save as Frappe File
        file_doc = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": output_filename,
                "attached_to_doctype": attached_to_doctype,
                "attached_to_name": attached_to_name,
                "folder": folder,
                "is_private": is_private,
                "content": compiled_bytes,
            }
        )
        file_doc.save(ignore_permissions=True)

        return file_doc

    def query(
        self,
        selector: str,
        field: Optional[str] = None,
        one: bool = False,
    ) -> Any:
        """
        Query elements in the Typst template.

        Args:
            selector: CSS-like selector for elements (e.g., "<note>")
            field: Specific field to extract (e.g., "value")
            one: Return only the first match

        Returns:
            Query results (depends on selector and options)
        """
        try:
            result = typst.query(self.files, selector, field=field, one=one)
            return result
        except Exception as e:
            frappe.throw(f"Typst query failed: {str(e)}")


def build(
    raw: Optional[Union[str, bytes]] = None,
    doc: Optional[str] = None,
    path: Optional[Union[str, Path]] = None,
    files: Optional[dict[str, Union[str, bytes, Path]]] = None,
) -> TypstBuilder:
    """
    Convenience function to build a TypstBuilder with a file loaded.

    Provide one of: raw, doc, files, or path parameters.

    Args:
        raw: Typst markup as string or bytes (calls read_string)
        doc: Frappe File document name (e.g., "FILE-000123") (calls read_file_doc)
        files: Dict of multiple files (calls read_files)
        path: Filesystem path to .typ file (calls read_file_path)

    Returns:
        TypstBuilder instance with template loaded

    Example:
        # From string
        builder = build(raw="#set page(width: 10cm, height: auto)\\n= Invoice\\nTotal: $500")
        file_doc = builder.save("invoice.pdf")

        # From Frappe File document
        builder = build(doc="FILE-000123")
        file_doc = builder.save("output.pdf")

        # From filesystem path
        builder = build(path="template.typ")
        file_doc = builder.save("output.pdf")

        # With dynamic values
        builder = build(raw="= Invoice #sys.inputs.invoice_no\\nAmount: $#sys.inputs.amount")
        file_doc = builder.save(
            "invoice.pdf",
            sys_inputs={"invoice_no": "INV-001", "amount": "1000"},
            attached_to_doctype="Sales Invoice",
            attached_to_name="INV-001"
        )
    """
    builder = TypstBuilder()

    # Load template based on provided parameter
    if raw is not None:
        builder.read_string(raw)
    elif doc is not None:
        builder.read_file_doc(doc)
    elif path is not None:
        builder.read_file_path(path)
    elif files is not None:
        builder.read_files(files)
    else:
        frappe.throw("Must provide one of: raw, doc, path, or files parameters")

    return builder
