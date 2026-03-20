# Copyright (c) 2025, and contributors
# For license information, please see license.txt

import json
from typing import Literal

import frappe
from frappe import _
from frappe.core.doctype.log_settings.log_settings import LogType
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

# Valid sync job operations (immutable)
VALID_SYNC_OPERATIONS = ("insert", "update", "delete")

# Valid sync job statuses (immutable)
SyncJobStatus = Literal[
    "Pending",
    "Queued",
    "Started",
    "Finished",
    "Failed",
    "Canceled",
    "Skipped",
    "Relayed",
    "No Target",
]


class SyncJob(Document, LogType):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        context: DF.Code | None
        current_data: DF.Code | None
        diff_summary: DF.Code | None
        insert_enabled: DF.Check
        update_enabled: DF.Check
        delete_enabled: DF.Check
        update_without_changes_enabled: DF.Check
        verbose_logging: DF.Check
        dry_run: DF.Check
        multiple_target_documents: DF.Code | None
        operation: DF.Literal["", "Insert", "Update", "Delete"]
        parent_sync_job: DF.Link | None
        source_document_type: DF.Link | None
        source_document_name: DF.DynamicLink | None
        status: DF.Literal[
            "Pending",
            "Queued",
            "Started",
            "Finished",
            "Failed",
            "Canceled",
            "Skipped",
            "Relayed",
            "No Target",
        ]
        sync_job_type: DF.Link
        target_document_type: DF.Link | None
        target_document_name: DF.DynamicLink | None
        task_id: DF.Link | None
        title: DF.Data | None
        trigger_type: DF.Literal[
            "Manual", "Scheduler", "Webhook", "API", "Document Hook"
        ]
        triggered_by_document_type: DF.Link | None
        triggered_by_document_name: DF.DynamicLink | None
        trigger_document_timestamp: DF.Datetime | None
        updated_data: DF.Code | None
    # end: auto-generated types

    def before_validate(self):
        """Set title before validation"""
        self.title = self.generate_title()

    def before_insert(self):
        """Set defaults before inserting"""
        # Set default status
        if not self.status:
            self.status = "Pending"

        # Set trigger document timestamp if trigger document is present
        if (
            self.triggered_by_document_type
            and self.triggered_by_document_name
            and not self.trigger_document_timestamp
        ):
            trigger_doc = get_document_even_if_deleted(
                self.triggered_by_document_type, self.triggered_by_document_name
            )
            self.trigger_document_timestamp = trigger_doc.modified

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
            if not self.source_document_type:
                self.source_document_type = job_type.source_document_type
            if not self.target_document_type:
                self.target_document_type = job_type.target_document_type

            # Allow override, otherwise use defaults from type
            if self.verbose_logging is None:
                self.verbose_logging = job_type.verbose_logging or 0

    def generate_title(self):
        """
        Generate title for sync job.

        Format:
        - If target: source_document_type > target_document_type: target_document_name
        - If no target: source_document_type: source_document_name
        - If no source name: source_document_type

        Returns:
            str: Generated title (max 140 chars)
        """
        # Has target
        if self.target_document_type and self.target_document_name:
            return f"{self.source_document_type} > {self.target_document_type}: {self.target_document_name}"[
                :140
            ]

        # No target - use source only
        if self.source_document_name:
            return f"{self.source_document_type}: {self.source_document_name}"[:140]
        else:
            return self.source_document_type[:140]

    def after_insert(self):
        """Enqueue sync job after insert via the Async Task system."""
        self._enqueue_async_task()

    def on_trash(self):
        """Cancel the linked async task on delete."""
        if self.task_id:
            try:
                task = frappe.get_doc("Async Task Log", self.task_id)
                task.cancel()
            except Exception:
                pass

    @frappe.whitelist()
    def cancel_sync(self, reason=None):
        """
        Cancel sync job (only Pending, Queued or Failed)

        Args:
            reason: Optional cancellation reason (passed to the linked async task)
        """
        if self.status not in ["Pending", "Queued", "Failed"]:
            frappe.throw(_("Cannot cancel job with status {0}").format(self.status))

        # Cancel async task if one is linked — its status update will call
        # on_async_task_status_update("Canceled") which calls _finish_job
        if self.task_id:
            try:
                task = frappe.get_doc("Async Task Log", self.task_id)
                task.cancel(message=reason)
                return
            except Exception:
                pass

        # Fallback: no task or task cancellation failed, finish directly
        self._finish_job(status="Canceled")

    @frappe.whitelist()
    def retry(self):
        """Retry failed sync job by retrying the linked async task."""
        if not self.task_id:
            frappe.throw(_("No async task linked to retry"))

        task = frappe.get_doc("Async Task Log", self.task_id)
        task.retry(now=True)

    @staticmethod
    def clear_old_logs(days: int = 30) -> None:
        """Delete old sync jobs (called by Frappe's log cleanup)"""
        table = frappe.qb.DocType("Sync Job")
        frappe.db.delete(
            table, filters=(table.modified < (Now() - Interval(days=days)))
        )

    def on_async_task_status_update(self, task, message=None):
        """
        Handle status updates from the linked Async Task Log.

        Called by AsyncTaskLog.notify_target_document when the async task status
        changes. Updates the sync job status to reflect the current execution state.

        Args:
            task: AsyncTaskLog document with the new status
            message: Optional status message
        """
        if task.status == "Pending" and (task.retry_count or 0) > 0:
            # Auto-retry: the dispatcher has reset the task to Pending for another attempt
            self.db_set({"status": "Pending"}, update_modified=False)
        elif task.status == "Queued":
            self.db_set(
                {"status": "Queued", "task_id": task.name}, update_modified=False
            )
        elif task.status == "Started":
            self.db_set(
                {"status": "Started", "task_id": task.name}, update_modified=False
            )
        elif task.status == "Failed":
            self.db_set({"status": "Failed"}, update_modified=False)
        elif task.status == "Canceled":
            self._finish_job(status="Canceled")
        # "Finished" — execute() already set the correct business status
        # (Finished / Skipped / No Target / Relayed) via _finish_job()

    def _enqueue_async_task(self):
        """
        Create an Async Task Log for this sync job and store the link.

        The Async Task Type for execute_sync_job has concurrency_limit=1, ensuring
        only one sync job runs at a time.

        Queue, timeout, and retry settings are read from the linked Sync Job Type
        and stored on the async task so the dispatcher and retry mechanism handle
        scheduling without extra logic here.
        """
        from tweaks.tweaks.doctype.async_task_log.async_task_log import (
            enqueue_async_task,
        )

        job_type = frappe.get_doc("Sync Job Type", self.sync_job_type)

        task = enqueue_async_task(
            "tweaks.tweaks.doctype.sync_job.sync_job.execute_sync_job",
            document_type="Sync Job",
            document_name=self.name,
            queue=job_type.queue or "default",
            timeout=job_type.timeout or 300,
            max_retries=job_type.max_retries or 0,
            retry_delay=(job_type.retry_delay or 0) * 60,  # convert minutes -> seconds
            sync_job_name=self.name,
        )
        self.db_set("task_id", task.name, update_modified=False)
        frappe.db.commit()

    @frappe.whitelist()
    def execute(self):
        """Execute the sync job"""
        try:

            # Load components
            source_doc = self.get_source_document()
            context = self.get_context()
            module = self._load_and_validate_module()

            # Call after_start hook if exists
            if hasattr(module, "after_start"):
                module.after_start(self, source_doc)

            # Execute based on mode
            has_execute = hasattr(module, "execute")
            if has_execute:
                target_doc, operation, diff = self._execute_bypass_mode(
                    module, source_doc, context
                )
            else:
                target_doc, operation, diff = self._execute_standard_mode(
                    module, source_doc, context
                )

            # Finalize
            if target_doc is not None:
                # Set operation and diff before finishing
                self.operation = operation.title()
                self.diff_summary = frappe.as_json(diff) if diff else None
                self._finish_job(
                    status="Finished",
                    target_doc=target_doc,
                    module=module,
                    source_doc=source_doc,
                )

        except Exception as e:
            self._handle_error(e)

    def get_source_document(self):
        """
        Load source document.
        Returns None if source_document_name is not set or if document doesn't exist.
        """
        if not self.source_document_name:
            return None

        return get_document_even_if_deleted(
            self.source_document_type, self.source_document_name
        )

    def get_trigger_document(self):
        """
        Load trigger document.
        Returns None if trigger_document_name is not set or if document doesn't exist.
        """
        if not self.triggered_by_document_name:
            return None

        return get_document_even_if_deleted(
            self.triggered_by_document_type, self.triggered_by_document_name
        )

    def get_target_document(self, for_update=False):
        """Load target document"""
        return frappe.get_doc(
            self.target_document_type, self.target_document_name, for_update=for_update
        )

    def get_context(self):
        """Parse JSON context"""
        return json.loads(self.context) if self.context else {}

    def _load_and_validate_module(self):
        """Load and validate sync job module"""
        from tweaks.utils.sync_job import (
            get_sync_job_module_dotted_path,
            validate_sync_job_module,
        )

        job_type = frappe.get_doc("Sync Job Type", self.sync_job_type)
        module_path = get_sync_job_module_dotted_path(job_type.module, job_type.name)
        module = frappe.get_module(module_path)

        # Validate module structure (hard validation)
        try:
            validate_sync_job_module(module, soft=False)
        except Exception:
            # Module validation error — set Failed and re-raise (no retry for config errors)
            self.status = "Failed"
            self.flags.ignore_links = True
            self.save(ignore_permissions=True)
            frappe.db.commit()
            raise

        return module

    def _execute_bypass_mode(self, module, source_doc, context):
        """Execute in bypass mode"""
        result = module.execute(self, source_doc)
        target_doc = result["target_doc"]
        operation = result["operation"]

        # Save target_document_type immediately
        if target_doc and not self.target_document_type:
            self.target_document_type = target_doc.doctype

        # For updates/deletes, save target_document_name immediately
        # For inserts, it will be set after save in the bypass execute function
        if target_doc and operation.lower() != "insert":
            self.target_document_name = target_doc.name
        elif target_doc and operation.lower() == "insert":
            # For inserts in bypass mode, the name should already be set after save in execute()
            self.target_document_name = target_doc.name

        return target_doc, operation, result.get("diff", {})

    def _execute_standard_mode(self, module, source_doc, context):
        """Execute in standard mode"""
        # Determine target document and operation
        if self.operation and self.operation.lower() == "insert":
            target_doc, operation, context = self._process_target_info(
                {"operation": "insert"}, context
            )
        elif self.target_document_name:
            target_doc, operation = self._get_predefined_target()
        else:
            target_doc, operation, context = self._discover_target(
                module, source_doc, context
            )

        if target_doc is None:
            # No target found or multiple targets handled
            return None, None, None

        # Execute based on operation
        if operation.lower() == "delete":
            diff = self._execute_delete_operation(module, source_doc, target_doc)
        else:
            diff = self._execute_insert_update_operation(
                module, source_doc, target_doc, operation
            )

        return target_doc, operation, diff

    def _get_predefined_target(self):
        """Get pre-specified target document"""
        if not self.operation:
            frappe.throw(
                _("Operation must be specified when target_document_name is provided")
            )

        target_doc = frappe.get_doc(
            self.target_document_type, self.target_document_name
        )
        return target_doc, self.operation.lower()

    def _discover_target(self, module, source_doc, context):
        """Discover target document(s)"""
        has_multiple = hasattr(module, "get_multiple_target_documents")

        if has_multiple:
            targets = module.get_multiple_target_documents(self, source_doc)

            if len(targets) > 1:
                self._handle_multiple_targets(targets, module)
                return None, None, context

            elif len(targets) == 1:
                target_info = targets[0]
                return self._process_target_info(target_info, context)

            else:
                # No targets found
                self._finish_job(status="No Target")
                return None, None, context

        else:
            target_info = module.get_target_document(self, source_doc)

            if not target_info:
                # No target found
                self._finish_job(status="No Target")
                return None, None, context

            return self._process_target_info(target_info, context)

    def _process_target_info(self, target_info, context):
        """
        Process target info dict and return target document, operation, and context.

        Args:
            target_info: Dict containing operation, target_document_type, target_document_name, context
            context: Current context dict

        Returns:
            Tuple of (target_doc, operation, context)
        """
        # Validate required key: operation is always required
        if "operation" not in target_info:
            frappe.throw(_("Target info must contain 'operation' key"))

        operation = target_info["operation"]
        self.operation = operation.title()

        # Normalize operation to lowercase for comparison
        operation_lower = operation.lower()

        # Validate operation is valid
        if operation_lower not in VALID_SYNC_OPERATIONS:
            frappe.throw(
                _("Invalid operation '{0}'. Must be one of: {1}").format(
                    operation, ", ".join(VALID_SYNC_OPERATIONS)
                )
            )

        # Get target_document_type from return dict, or use the one from sync_job_type
        target_document_type = target_info.get("target_document_type")
        if not target_document_type:
            # Fall back to sync_job_type's target_document_type
            target_document_type = self.target_document_type

        # Get target_document_name (required for update/delete)
        target_document_name = target_info.get("target_document_name")

        # Context can override existing context
        context = target_info.get("context", context)

        # Validate target_document_name is provided for update/delete operations
        if operation_lower in ["update", "delete"] and not target_document_name:
            frappe.throw(
                _("target_document_name is required for {0} operation").format(
                    operation
                )
            )

        # Save target_document_type if not already set
        if target_document_type and not self.target_document_type:
            self.target_document_type = target_document_type

        # For updates/deletes, save target_document_name immediately
        # For inserts, it will be set after save (may be auto-generated)
        if operation_lower != "insert" and target_document_name:
            self.target_document_name = target_document_name

        # Load the actual document for processing
        if not target_document_type:
            # No target specified - finish job without target
            self._finish_job(status="No Target")
            return None, None, context
        elif operation_lower == "insert":
            self.target_document_name = None  # Will be set after insert
            target_doc = frappe.new_doc(target_document_type)
        else:
            # Load the target document for update or delete
            try:
                target_doc = frappe.get_doc(
                    target_document_type, target_document_name, for_update=True
                )
            except frappe.DoesNotExistError:
                if operation_lower == "delete":
                    # Target doesn't exist, nothing to delete - finish job
                    self._finish_job(status="No Target")
                    return None, None, context
                else:
                    # For update, target must exist
                    raise

        return target_doc, operation, context

    def _handle_multiple_targets(self, targets, module=None):
        """Handle multiple target documents by spawning child jobs"""
        from tweaks.utils.sync_job import create_sync_job

        # Call before_relay hook if exists
        if module and hasattr(module, "before_relay"):
            source_doc = self.get_source_document()
            module.before_relay(self, source_doc, targets)

        child_jobs = []
        for target_info in targets:
            child_job = create_sync_job(
                sync_job_type=self.sync_job_type,
                source_document_name=self.source_document_name,
                source_document_type=self.source_document_type,
                context=target_info.get("context", {}),
                operation=target_info["operation"].title(),
                target_document_type=target_info["target_document_type"],
                target_document_name=target_info.get("target_document_name"),
                parent_sync_job=self.name,
                trigger_type=self.trigger_type,
                triggered_by_document_name=self.triggered_by_document_name,
                triggered_by_document_type=self.triggered_by_document_type,
                trigger_document_timestamp=self.trigger_document_timestamp,
                dry_run=self.dry_run,
            )

            child_jobs.append(
                {
                    "target_document_type": target_info["target_document_type"],
                    "target_document_name": target_info.get("target_document_name"),
                    "operation": target_info["operation"],
                    "context": target_info.get("context", {}),
                    "sync_job": child_job.name,
                }
            )

        # Store child job references
        self.multiple_target_documents = frappe.as_json(child_jobs)

        # Get source document once for both hooks
        source_doc = self.get_source_document()

        # Call after_relay hook before finishing
        if module and hasattr(module, "after_relay"):
            module.after_relay(self, source_doc, child_jobs)

        # Finish job with Relayed status (will also call finished hook)
        self._finish_job(
            status="Relayed",
            target_doc=None,
            module=module,
            source_doc=source_doc,
        )

    def _finish_job(
        self,
        status: SyncJobStatus,
        target_doc=None,
        module=None,
        source_doc=None,
        stop_execution: bool = False,
        stop_message: str | None = None,
    ):
        """
        Unified method to finish sync job with various statuses.

        This method handles the common finishing logic:
        - Sets job status
        - Saves and commits the job
        - Calls the finished hook if applicable
        - Optionally raises StopIteration to halt execution

        Note: Callers should set self.operation and self.diff_summary before calling this method.

        Args:
            status: Job status to set (e.g., "Finished", "Skipped", "Relayed", "No Target")
            target_doc: Target document (optional)
            module: Sync job module (optional)
            source_doc: Source document (optional)
            stop_execution: Whether to raise StopIteration to halt execution
            stop_message: Message for StopIteration exception
        """
        # Set status
        self.status = status

        # Clear current_data and updated_data if verbose_logging is disabled
        # and status is one of the completion states
        if not self.get("verbose_logging") and status in [
            "Finished",
            "Canceled",
            "Skipped",
            "No Target",
            "Relayed",
        ]:
            self.current_data = None
            self.updated_data = None

        # Save and commit
        self.flags.ignore_links = True
        self.save(ignore_permissions=True)
        frappe.db.commit()

        # Call finished hook if module is provided and has the hook
        if module and hasattr(module, "finished"):
            module.finished(self, source_doc, target_doc)

        # Stop execution if requested
        if stop_execution:
            raise StopIteration(stop_message or f"Sync job {status.lower()}")

    def _execute_delete_operation(self, module, source_doc, target_doc):
        """Execute delete operation"""
        # Check if we should skip delete operations
        if not self.get("delete_enabled", True):
            self._finish_job(
                status="Skipped",
                target_doc=target_doc,
                module=module,
                source_doc=source_doc,
                stop_execution=True,
                stop_message="Sync job skipped",
            )
            return {}

        # Capture current state before delete
        if target_doc:
            self.current_data = target_doc.as_json()

        # Dry run mode: finish without saving, set status to Skipped
        if self.get("dry_run"):
            # Set operation and diff before finishing
            self.operation = operation.title()
            self.diff_summary = frappe.as_json(diff) if diff else None
            self._finish_job(
                status="Skipped",
                target_doc=target_doc,
                module=module,
                source_doc=source_doc,
                stop_execution=True,
                stop_message="Sync job skipped (dry run)",
            )

        # Call before_sync hook
        if hasattr(module, "before_sync"):
            module.before_sync(self, source_doc, target_doc)

        # Delete document
        target_doc.delete(ignore_permissions=True)

        # Call after_sync hook
        if hasattr(module, "after_sync"):
            module.after_sync(self, source_doc, target_doc)

        return {}

    def _execute_insert_update_operation(
        self, module, source_doc, target_doc, operation
    ):
        """Execute insert or update operation"""
        # Check if we should skip based on operation type
        if operation.lower() == "insert" and not self.get("insert_enabled", True):
            self._finish_job(
                status="Skipped",
                target_doc=target_doc,
                module=module,
                source_doc=source_doc,
                stop_execution=True,
                stop_message="Sync job skipped",
            )
            return {}

        if operation.lower() == "update" and not self.get("update_enabled", True):
            self._finish_job(
                status="Skipped",
                target_doc=target_doc,
                module=module,
                source_doc=source_doc,
                stop_execution=True,
                stop_message="Sync job skipped",
            )
            return {}

        # Capture current state for existing docs
        if target_doc and not target_doc.is_new():
            target_doc.get_latest()
            self.current_data = target_doc.as_json()

        # Update target document
        module.update_target_doc(self, source_doc, target_doc)

        # Capture updated state
        self.updated_data = target_doc.as_json()

        # Get diff after mapping but before saving
        diff = target_doc.get_diff() if not target_doc.is_new() else {}

        # Dry run mode: finish without saving, set status to Skipped
        if self.get("dry_run"):
            # Set operation and diff before finishing
            self.operation = operation.title()
            self.diff_summary = frappe.as_json(diff) if diff else None
            self._finish_job(
                status="Skipped",
                target_doc=target_doc,
                module=module,
                source_doc=source_doc,
                stop_execution=True,
                stop_message="Sync job skipped (dry run)",
            )

        # Skip update if no changes detected (unless update_without_changes_enabled is True to force update anyway)
        if (
            operation.lower() == "update"
            and not self.get("update_without_changes_enabled", False)
            and not diff
        ):
            self._finish_job(
                status="Skipped",
                target_doc=target_doc,
                module=module,
                source_doc=source_doc,
                stop_execution=True,
                stop_message="Sync job skipped",
            )
            return {}

        # Call before_sync hook
        if hasattr(module, "before_sync"):
            module.before_sync(self, source_doc, target_doc)

        # Save document
        target_doc.save(ignore_permissions=True)

        # Set target_document_name after save (for inserts with auto-generated names)
        self.target_document_name = target_doc.name

        # Call after_sync hook
        if hasattr(module, "after_sync"):
            module.after_sync(self, source_doc, target_doc)

        # Capture updated state again
        self.updated_data = target_doc.as_json()

        return diff

    def _handle_error(self, e):
        """Handle errors during sync execution"""
        # Don't handle StopIteration (used for skipped jobs)
        if isinstance(e, StopIteration):
            return

        self.status = "Failed"

        self.flags.ignore_links = True
        self.save(ignore_permissions=True)
        frappe.db.commit()

        raise  # re-raise so the async task records failure and handles auto-retry


@frappe.whitelist()
def clear_all_logs() -> None:
    """
    Clear all Sync Job logs.

    This function is whitelisted and can only be called by System Managers.
    It truncates the entire Sync Job table.
    """
    frappe.only_for("System Manager")
    frappe.db.truncate("Sync Job")


def execute_sync_job(sync_job_name):
    """
    Execute sync job (runs in background via Async Task system).

    Called by the Async Task worker. Concurrency is enforced by the
    Async Task Type for this method (concurrency_limit=1), so only one
    sync job runs at a time without requiring a manual Redis lock.

    Args:
        sync_job_name: Name of Sync Job document
    """
    sync_job = frappe.get_doc("Sync Job", sync_job_name, for_update=1)
    sync_job.execute()


def get_document_even_if_deleted(doctype, name):
    """
    Load document even if it has been deleted.

    Args:
        doctype: Document type
        name: Document name
    """
    # Check if doctype is virtual
    meta = frappe.get_meta(doctype)
    is_virtual = meta.get("is_virtual")

    # For virtual doctypes, use frappe.get_doc directly
    # as frappe.db.get_value will fail for them
    if is_virtual:
        try:
            return frappe.get_doc(doctype, name)
        except frappe.DoesNotExistError:
            frappe.throw(
                _("{0} {1} not found").format(_(doctype), name),
                frappe.DoesNotExistError(doctype=doctype),
            )

    try:
        doc = frappe.db.get_value(doctype, name)
        if not doc:
            raise frappe.DoesNotExistError
        return frappe.get_doc(doctype, name)
    except frappe.DoesNotExistError:
        pass

    # Check if document was deleted
    deleted_doc = frappe.db.get_value(
        "Deleted Document",
        filters={"deleted_doctype": doctype, "deleted_name": name},
        fieldname=["data", "creation"],
        order_by="creation desc",
        as_dict=1,
    )
    if deleted_doc:
        deleted_doc = frappe.get_doc(json.loads(deleted_doc["data"]))
        deleted_doc.modified = deleted_doc.creation
        deleted_doc.flags.is_deleted = True
        return deleted_doc

    frappe.throw(
        _("{0} {1} not found").format(_(doctype), name),
        frappe.DoesNotExistError(doctype=doctype),
    )
