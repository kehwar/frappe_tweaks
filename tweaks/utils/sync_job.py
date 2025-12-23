# Copyright (c) 2025, and contributors
# For license information, please see license.txt

"""
Utilities for Sync Job framework
"""

import json

import frappe
from frappe import _
from frappe.modules import scrub
from frappe.utils import now


@frappe.whitelist()
def enqueue_sync_job(
    sync_job_type,
    source_doc=None,
    source_document_type=None,
    source_document_name=None,
    operation=None,
    context=None,
    target_doc=None,
    target_document_type=None,
    target_document_name=None,
    parent_sync_job=None,
    queue=None,
    timeout=None,
    retry_delay=None,
    max_retries=None,
    trigger_type="Manual",
    triggered_by_doc=None,
    triggered_by_document_type=None,
    triggered_by_document_name=None,
    queue_on_insert=True,
    dry_run=False,
    insert_enabled=True,
    update_enabled=True,
    delete_enabled=True,
    update_without_changes_enabled=False,
):
    """
    Create and enqueue a sync job

    Args:
        sync_job_type: Name of Sync Job Type
        source_doc: Optional source document object (extracts type and name from it)
        source_document_type: Optional pre-specified source document type (overrides job type default)
        source_document_name: Optional name of source document (can be None if source was deleted)
        operation: Optional pre-specified operation (Insert/Update/Delete)
        context: Optional context dictionary (required when source_document_name is None)
        target_doc: Optional target document object (extracts type and name from it)
        target_document_type: Optional pre-specified target document type (overrides job type default)
        target_document_name: Optional pre-specified target document name
        parent_sync_job: Optional parent sync job name
        queue: Optional queue override
        timeout: Optional timeout override
        retry_delay: Optional retry delay override
        max_retries: Optional max retries override
        trigger_type: How the job was triggered (default: Manual)
        triggered_by_doc: Optional document that triggered this sync job
        triggered_by_document_type: Optional document type that triggered this sync job
        triggered_by_document_name: Optional document name that triggered this sync job
        queue_on_insert: Whether to queue job on insert (default: True)
        dry_run: Whether to calculate diff only without saving (default: False)
        insert_enabled: Allow insert operations (default: True)
        update_enabled: Allow update operations (default: True)
        delete_enabled: Allow delete operations (default: True)
        update_without_changes_enabled: Save even if no changes (default: False)

    Returns:
        Sync Job document
    """
    # Get Sync Job Type
    job_type = frappe.get_doc("Sync Job Type", sync_job_type)

    # Extract source info from source_doc if provided
    if source_doc:
        if not source_document_type:
            source_document_type = source_doc.doctype
        if not source_document_name and source_doc.name:
            source_document_name = source_doc.name

    # Use job_type default if source_document_type not specified
    if not source_document_type:
        source_document_type = job_type.source_document_type

    # Extract target info from target_doc if provided
    if target_doc:
        if not target_document_type:
            target_document_type = target_doc.doctype
        if not target_document_name and target_doc.name:
            target_document_name = target_doc.name

    # Use job_type default if target_document_type not specified
    if not target_document_type:
        target_document_type = job_type.target_document_type

    # Extract triggered_by info from triggered_by_doc if provided
    if triggered_by_doc:
        if not triggered_by_document_type:
            triggered_by_document_type = triggered_by_doc.doctype
        if not triggered_by_document_name and triggered_by_doc.name:
            triggered_by_document_name = triggered_by_doc.name

    # Create Sync Job document
    sync_job = frappe.get_doc(
        {
            "doctype": "Sync Job",
            "sync_job_type": sync_job_type,
            "source_document_type": source_document_type,
            "source_document_name": source_document_name,
            "target_document_type": target_document_type,
            "target_document_name": target_document_name,
            "triggered_by_document_type": triggered_by_document_type,
            "triggered_by_document_name": triggered_by_document_name,
            "operation": operation.title() if operation else None,
            "context": frappe.as_json(context) if context else None,
            "parent_sync_job": parent_sync_job,
            "queue": queue or job_type.queue,
            "timeout": timeout or job_type.timeout,
            "retry_delay": retry_delay or job_type.retry_delay,
            "max_retries": max_retries or job_type.max_retries,
            "trigger_type": trigger_type,
            "queue_on_insert": queue_on_insert,
            "dry_run": dry_run,
            "insert_enabled": insert_enabled,
            "update_enabled": update_enabled,
            "delete_enabled": delete_enabled,
            "update_without_changes_enabled": update_without_changes_enabled,
        }
    )

    sync_job.flags.ignore_links = True
    sync_job.insert(ignore_permissions=True)
    frappe.db.commit()

    return sync_job


def get_sync_job_module_dotted_path(module, name):
    """
    Get dotted path to sync job module

    Args:
        module: Module name (e.g. "tweaks")
        name: Sync Job Type name (e.g. "SAP Customer Sync")

    Returns:
        Dotted module path (e.g. "tweaks.tweaks.sync_job_type.sap_customer_sync.sap_customer_sync")
    """
    app = frappe.local.module_app.get(scrub(module))
    scrubbed_name = scrub(name)
    return f"{app}.{scrub(module)}.sync_job_type.{scrubbed_name}.{scrubbed_name}"


def validate_sync_job_module(module, soft=False):
    """
    Validate sync job module structure

    Module must have either:
    - execute() function (bypass mode)
    - get_target_document() AND update_target_doc() functions (standard mode - single target)
    - get_multiple_target_documents() AND update_target_doc() functions (standard mode - multiple targets)

    Args:
        module: Python module object
        soft: If True, log warning instead of raising exception

    Raises:
        ValidationError: If validation fails and soft=False
    """
    has_execute = hasattr(module, "execute")
    has_get_target = hasattr(module, "get_target_document")
    has_get_multiple_targets = hasattr(module, "get_multiple_target_documents")
    has_update_target = hasattr(module, "update_target_doc")

    # Valid configurations:
    # 1. Bypass mode: execute() exists
    # 2. Standard single target: get_target_document() AND update_target_doc()
    # 3. Standard multiple targets: get_multiple_target_documents() AND update_target_doc()
    is_valid = (
        has_execute
        or (has_get_target and has_update_target)
        or (has_get_multiple_targets and has_update_target)
    )

    if not is_valid:
        msg = _(
            "Sync job module must have either execute() function (bypass mode) "
            "or update_target_doc() with get_target_document() or get_multiple_target_documents() (standard mode)"
        )

        if soft:
            frappe.log_error(msg, "Sync Job Module Validation")
        else:
            frappe.throw(msg, frappe.ValidationError)


@frappe.whitelist()
def check_sync_job_module_exists(module, name):
    """
    Check if sync job module exists (for JS callback)

    Args:
        module: Module name
        name: Sync Job Type name

    Returns:
        True if module exists, False otherwise
    """
    try:
        module_path = get_sync_job_module_dotted_path(module, name)
        frappe.get_module(module_path)
        return True
    except ImportError:
        return False


def auto_retry_failed_jobs():
    """
    Auto-retry failed jobs that are due for retry

    Called by scheduler
    """
    from frappe.query_builder import Order
    from frappe.query_builder.functions import Now

    # Query failed jobs due for retry
    SyncJob = frappe.qb.DocType("Sync Job")

    failed_jobs = (
        frappe.qb.from_(SyncJob)
        .select(SyncJob.name, SyncJob.retry_count, SyncJob.max_retries)
        .where(SyncJob.status == "Failed")
        .where(SyncJob.retry_count < SyncJob.max_retries)
        .where(SyncJob.retry_after <= Now())
        .orderby(SyncJob.retry_after, order=Order.asc)
        .run(as_dict=True)
    )

    # Retry each job
    for job_data in failed_jobs:
        try:
            job = frappe.get_doc("Sync Job", job_data.name)
            job.retry()
        except Exception:
            frappe.log_error(
                f"Failed to auto-retry Sync Job {job_data.name}", "Auto Retry Sync Job"
            )
