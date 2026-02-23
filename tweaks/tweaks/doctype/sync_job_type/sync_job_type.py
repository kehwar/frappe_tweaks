# Copyright (c) 2025, and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SyncJobType(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        disabled: DF.Check
        is_standard: DF.Literal["Yes", "No"]
        max_retries: DF.Int
        module: DF.Link
        queue: DF.Data | None
        retry_delay: DF.Int
        source_document_type: DF.Link
        sync_job_type_name: DF.Data
        target_document_type: DF.Link
        timeout: DF.Int
        serialize_execution: DF.Check
        verbose_logging: DF.Check
    # end: auto-generated types

    def validate(self):
        """Validate sync job type"""
        # Set module from source doctype if not set
        if not self.module:
            self.module = frappe.db.get_value(
                "DocType", self.source_document_type, "module"
            )

        # Set is_standard based on developer mode
        if not self.is_standard:
            self.is_standard = "No"
            if (
                frappe.session.user == "Administrator"
                and getattr(frappe.local.conf, "developer_mode", 0) == 1
            ):
                self.is_standard = "Yes"

        if self.is_standard == "No":
            # Allow only script manager to edit
            frappe.only_for("Script Manager", True)

            if frappe.db.get_value("Sync Job Type", self.name, "is_standard") == "Yes":
                frappe.throw(
                    _(
                        "Cannot edit a standard sync job type. Please duplicate and create a new one"
                    )
                )

        if self.is_standard == "Yes" and frappe.session.user != "Administrator":
            frappe.throw(
                _(
                    "Only Administrator can save a standard sync job type. Please rename and save."
                )
            )

        # Soft validate sync job module if exists
        if self.is_standard == "Yes":
            try:
                from tweaks.utils.sync_job import (
                    get_sync_job_module_dotted_path,
                    validate_sync_job_module,
                )

                module_path = get_sync_job_module_dotted_path(self.module, self.name)
                module = frappe.get_module(module_path)
                validate_sync_job_module(module, soft=True)  # Warning only
            except ImportError:
                pass  # Module doesn't exist yet

    def on_update(self):
        """Export to files if standard"""
        self.export_doc()

    def export_doc(self):
        """Export sync job type to files"""
        if frappe.flags.in_import:
            return

        if (
            self.is_standard == "Yes"
            and (frappe.local.conf.get("developer_mode") or 0) == 1
        ):
            from frappe.modules.export_file import export_to_files

            export_to_files(
                record_list=[["Sync Job Type", self.name]],
                record_module=self.module,
                create_init=True,
            )

            self.create_sync_job_boilerplate()

    def create_sync_job_boilerplate(self):
        """Create boilerplate files for sync job"""
        if self.is_standard == "Yes":
            from tweaks.utils.modules import make_boilerplate

            # Use Sync Job Type's own boilerplate templates
            make_boilerplate(
                "controller._py",
                self,
                {"name": self.name},
                template_module="Tweaks",
                template_doctype="Sync Job Type",
            )
