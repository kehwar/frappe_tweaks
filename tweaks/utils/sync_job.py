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
    source_doc_name,
    filters=None,
    context=None,
    operation=None,
    target_document_name=None,
    parent_sync_job=None,
    queue=None,
    timeout=None,
    retry_delay=None,
    max_retries=None,
    trigger_type="Manual",
):
    """
    Create and enqueue a sync job

    Args:
        sync_job_type: Name of Sync Job Type
        source_doc_name: Name of source document
        filters: Optional filter dictionary
        context: Optional context dictionary
        operation: Optional pre-specified operation (Insert/Update/Delete)
        target_document_name: Optional pre-specified target document name
        parent_sync_job: Optional parent sync job name
        queue: Optional queue override
        timeout: Optional timeout override
        retry_delay: Optional retry delay override
        max_retries: Optional max retries override
        trigger_type: How the job was triggered (default: Manual)

    Returns:
        Sync Job document
    """
    # Get Sync Job Type
    job_type = frappe.get_doc("Sync Job Type", sync_job_type)

    # Create Sync Job document
    sync_job = frappe.get_doc(
        {
            "doctype": "Sync Job",
            "sync_job_type": sync_job_type,
            "source_doctype": job_type.source_doctype,
            "source_document_name": source_doc_name,
            "target_doctype": job_type.target_doctype,
            "target_document_name": target_document_name,
            "operation": operation,
            "filters": json.dumps(filters) if filters else None,
            "context": json.dumps(context) if context else None,
            "parent_sync_job": parent_sync_job,
            "queue": queue or job_type.queue,
            "timeout": timeout or job_type.timeout,
            "retry_delay": retry_delay or job_type.retry_delay,
            "max_retries": max_retries or job_type.max_retries,
            "trigger_type": trigger_type,
        }
    )

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
    - get_target_document() AND get_field_mapping() functions (standard mode)

    Args:
        module: Python module object
        soft: If True, log warning instead of raising exception

    Raises:
        ValidationError: If validation fails and soft=False
    """
    has_execute = hasattr(module, "execute")
    has_get_target = hasattr(module, "get_target_document")
    has_get_mapping = hasattr(module, "get_field_mapping")

    if not has_execute and not (has_get_target and has_get_mapping):
        msg = _(
            "Sync job module must have either execute() function or both get_target_document() and get_field_mapping() functions"
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
