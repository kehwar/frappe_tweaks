# Copyright (c) 2025, and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.core.doctype.log_settings.log_settings import LogType
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import add_to_date, create_batch, now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue


class SyncJob(Document, LogType):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        cancel_reason: DF.LongText | None
        context: DF.Code | None
        current_data: DF.Code | None
        diff_summary: DF.Code | None
        ended_at: DF.Datetime | None
        error_message: DF.LongText | None
        job_id: DF.Data | None
        max_retries: DF.Int
        multiple_target_documents: DF.Code | None
        operation: DF.Literal["", "Insert", "Update", "Delete"]
        parent_sync_job: DF.Link | None
        queue: DF.Data | None
        retry_after: DF.Datetime | None
        retry_count: DF.Int
        retry_delay: DF.Int
        source_doctype: DF.Link | None
        source_document_name: DF.DynamicLink | None
        started_at: DF.Datetime | None
        status: DF.Literal["Queued", "Started", "Finished", "Failed", "Canceled"]
        sync_job_type: DF.Link
        target_doctype: DF.Link | None
        target_document_name: DF.DynamicLink | None
        time_taken: DF.Duration | None
        timeout: DF.Int
        title: DF.Data | None
        trigger_type: DF.Literal[
            "Manual", "Scheduler", "Webhook", "API", "Document Hook"
        ]
        updated_data: DF.Code | None
    # end: auto-generated types

    def before_insert(self):
        """Set defaults before inserting"""
        # Set default status
        if not self.status:
            self.status = "Queued"

        # Auto-generate title
        if not self.title:
            self.title = f"{self.source_doctype}:{self.source_document_name}"

        # Validate context JSON
        if self.context:
            try:
                json.loads(self.context)
            except json.JSONDecodeError as e:
                frappe.throw(_("Invalid context JSON: {0}").format(str(e)))

        # Fetch from Sync Job Type
        if self.sync_job_type:
            job_type = frappe.get_doc("Sync Job Type", self.sync_job_type)

            # Fetch doctypes
            if not self.source_doctype:
                self.source_doctype = job_type.source_doctype
            if not self.target_doctype:
                self.target_doctype = job_type.target_doctype

            # Allow override, otherwise use defaults from type
            if self.queue is None:
                self.queue = job_type.queue or "default"
            if self.timeout is None:
                self.timeout = job_type.timeout or 300
            if self.retry_delay is None:
                self.retry_delay = job_type.retry_delay or 5
            if self.max_retries is None:
                self.max_retries = job_type.max_retries or 3

    def after_insert(self):
        """Enqueue sync job after insert"""
        enqueue(
            generate_sync,
            queue=self.queue or "default",
            timeout=self.timeout or 300,
            sync_job_name=self.name,
            enqueue_after_commit=True,
        )

    def on_trash(self):
        """Cancel background job if queued"""
        if self.status == "Queued":
            self.cancel_sync()

    def cancel_sync(self, reason=None):
        """
        Cancel sync job (only Queued or Failed)

        Args:
            reason: Optional cancellation reason
        """
        if self.status not in ["Queued", "Failed"]:
            frappe.throw(_("Cannot cancel job with status {0}").format(self.status))

        # Stop RQ job if exists
        if self.job_id:
            try:
                job = frappe.get_doc("RQ Job", self.job_id)
                if self.status == "Queued":
                    job.delete()
            except Exception:
                pass  # Job may not exist or already processed

        self.status = "Canceled"
        if reason:
            self.cancel_reason = reason
        self.ended_at = now()
        self.save(ignore_permissions=True)

    @frappe.whitelist()
    def retry(self):
        """Retry failed sync job"""
        # Increment retry count
        self.retry_count = (self.retry_count or 0) + 1

        # Set retry_after timestamp
        self.retry_after = add_to_date(now(), minutes=self.retry_delay or 5)

        # Reset status and error
        self.status = "Queued"
        self.error_message = None

        self.save(ignore_permissions=True)

        # Re-enqueue
        enqueue(
            generate_sync,
            queue=self.queue or "default",
            timeout=self.timeout or 300,
            sync_job_name=self.name,
        )

    @staticmethod
    def clear_old_logs(days: int = 30) -> None:
        """Delete old sync jobs (called by Frappe's log cleanup)"""
        table = frappe.qb.DocType("Sync Job")
        frappe.db.delete(
            table, filters=(table.modified < (Now() - Interval(days=days)))
        )


def update_job_id(sync_job_name):
    """Update job_id when job starts running"""
    from rq import get_current_job

    job = get_current_job()

    frappe.db.set_value(
        "Sync Job",
        sync_job_name,
        {
            "job_id": job and job.id,
            "status": "Started",
            "started_at": now(),
        },
        update_modified=False,
    )

    frappe.db.commit()


def generate_sync(sync_job_name):
    """
    Execute sync job (runs in background)

    Args:
        sync_job_name: Name of Sync Job document
    """

    update_job_id(sync_job_name)

    sync_job = frappe.get_doc("Sync Job", sync_job_name)
    job_type = frappe.get_doc("Sync Job Type", sync_job.sync_job_type)

    try:
        # Load source document
        source_doc = frappe.get_doc(
            sync_job.source_doctype, sync_job.source_document_name
        )

        # Parse JSON fields
        context = json.loads(sync_job.context) if sync_job.context else {}

        # Load sync job module
        from tweaks.utils.sync_job import (
            get_sync_job_module_dotted_path,
            validate_sync_job_module,
        )

        module_path = get_sync_job_module_dotted_path(job_type.module, job_type.name)
        module = frappe.get_module(module_path)

        # Validate module structure (hard validation)
        try:
            validate_sync_job_module(module, soft=False)
        except Exception as e:
            # Module validation error - don't increment retry_count
            sync_job.status = "Failed"
            sync_job.error_message = _("Module validation failed: {0}").format(str(e))
            sync_job.ended_at = now()
            sync_job.save(ignore_permissions=True)
            frappe.db.commit()
            return

        # Check execution mode
        has_execute = hasattr(module, "execute")

        if has_execute:
            # BYPASS MODE
            result = module.execute(sync_job, source_doc, context)
            target_doc = result["target_doc"]
            operation = result["operation"]
            diff = result.get("diff", {})

        else:
            # STANDARD MODE

            # Determine target document and operation
            if sync_job.target_document_name:
                # Pre-specified target
                if not sync_job.operation:
                    frappe.throw(
                        _(
                            "Operation must be specified when target_document_name is provided"
                        )
                    )

                target_doc = frappe.get_doc(
                    sync_job.target_doctype, sync_job.target_document_name
                )
                operation = sync_job.operation.lower()

            else:
                # Discover target(s)
                has_multiple = hasattr(module, "get_multiple_target_documents")

                if has_multiple:
                    # Check for multiple targets
                    targets = module.get_multiple_target_documents(
                        sync_job,
                        source_doc,
                        sync_job.get("create_missing", True),
                        context,
                    )

                    if len(targets) > 1:
                        # Spawn child jobs
                        from tweaks.utils.sync_job import enqueue_sync_job

                        child_jobs = []
                        for target_info in targets:
                            child_job = enqueue_sync_job(
                                sync_job_type=sync_job.sync_job_type,
                                source_doc_name=sync_job.source_document_name,
                                context=target_info.get("context", {}),
                                operation=target_info["operation"].title(),
                                target_document_name=target_info["target_doc"].name,
                                parent_sync_job=sync_job.name,
                                queue=sync_job.queue,
                                timeout=sync_job.timeout,
                                retry_delay=sync_job.retry_delay,
                                max_retries=sync_job.max_retries,
                            )

                            child_jobs.append(
                                {
                                    "target_doc": target_info["target_doc"].name,
                                    "operation": target_info["operation"],
                                    "context": target_info.get("context", {}),
                                    "sync_job": child_job.name,
                                }
                            )

                        # Store child job references
                        sync_job.multiple_target_documents = frappe.as_json(child_jobs)
                        sync_job.status = "Finished"
                        sync_job.ended_at = now()
                        sync_job.save(ignore_permissions=True)
                        frappe.db.commit()

                        # Publish completion event
                        frappe.publish_realtime(
                            "sync_job_completed",
                            {
                                "sync_job": sync_job.name,
                                "status": "Finished",
                                "children": len(child_jobs),
                            },
                            after_commit=True,
                        )
                        return

                    elif len(targets) == 1:
                        # Single target from get_multiple
                        target_doc = targets[0]["target_doc"]
                        operation = targets[0]["operation"]
                        context = targets[0].get("context", context)

                    else:
                        # No targets found
                        sync_job.status = "Finished"
                        sync_job.ended_at = now()
                        sync_job.save(ignore_permissions=True)
                        frappe.db.commit()
                        return

                else:
                    # Single target
                    target_doc, operation = module.get_target_document(
                        sync_job,
                        source_doc,
                        sync_job.get("create_missing", True),
                        context,
                    )

            # Execute sync based on operation
            if operation.lower() == "delete":
                # Delete operation - skip field mapping

                # Capture current state before delete
                if target_doc:
                    sync_job.current_data = target_doc.as_json()

                # Call before_sync hook
                if hasattr(module, "before_sync"):
                    module.before_sync(
                        sync_job, source_doc, target_doc, operation, context
                    )

                # Delete document
                target_doc.delete(ignore_permissions=True)

                # Call after_sync hook
                if hasattr(module, "after_sync"):
                    module.after_sync(
                        sync_job, source_doc, target_doc, operation, context
                    )

                diff = {}

            else:
                # Insert or Update operation

                # Capture current state for existing docs
                if target_doc and not target_doc.is_new():
                    target_doc.get_latest()
                    sync_job.current_data = target_doc.as_json()

                # Get field mapping
                field_mapping = module.get_field_mapping(
                    sync_job, source_doc, operation, context
                )

                # Apply field mapping
                target_doc.update(field_mapping)

                # Get diff after mapping but before saving
                diff = target_doc.get_diff() if not target_doc.is_new() else {}

                # Call before_sync hook
                if hasattr(module, "before_sync"):
                    module.before_sync(
                        sync_job, source_doc, target_doc, operation, context
                    )

                # Save document
                target_doc.flags.ignore_permissions = True
                target_doc.flags.ignore_links = True
                target_doc.save()

                # Update link field if provided
                if hasattr(module, "update_link_field"):
                    module.update_link_field(
                        sync_job, source_doc, target_doc, operation, context
                    )

                # Call after_sync hook
                if hasattr(module, "after_sync"):
                    module.after_sync(
                        sync_job, source_doc, target_doc, operation, context
                    )

                # Capture updated state
                sync_job.updated_data = target_doc.as_json()
                sync_job.target_document_name = target_doc.name

        # Save results
        sync_job.diff_summary = frappe.as_json(diff)
        sync_job.operation = operation.title()
        sync_job.status = "Finished"
        sync_job.ended_at = now()

        if sync_job.started_at and sync_job.ended_at:
            sync_job.time_taken = time_diff_in_seconds(
                sync_job.ended_at, sync_job.started_at
            )

        sync_job.save(ignore_permissions=True)
        frappe.db.commit()

        # Publish completion event
        frappe.publish_realtime(
            "sync_job_completed",
            {"sync_job": sync_job.name, "status": "Finished"},
            after_commit=True,
        )

    except Exception as e:
        # Handle errors
        sync_job.status = "Failed"
        sync_job.error_message = frappe.get_traceback(with_context=True)
        sync_job.ended_at = now()

        # Set retry_after timestamp
        if (sync_job.retry_count or 0) < sync_job.max_retries:
            sync_job.retry_after = add_to_date(now(), minutes=sync_job.retry_delay or 5)

        sync_job.save(ignore_permissions=True)
        frappe.db.commit()

        # Publish failure event
        frappe.publish_realtime(
            "sync_job_completed",
            {"sync_job": sync_job.name, "status": "Failed"},
            after_commit=True,
        )
