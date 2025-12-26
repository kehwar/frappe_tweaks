# Copyright (c) 2025, and contributors
# For license information, please see license.txt

import frappe

# Track hook calls for testing
hook_calls = []


def get_target_document(sync_job, source_doc):
    """Get target document for sync"""
    hook_calls.append(("get_target_document", sync_job.name))
    
    # Return insert operation for testing
    return {
        "operation": "insert",
    }


def update_target_doc(sync_job, source_doc, target_doc):
    """Update target document with data from source"""
    hook_calls.append(("update_target_doc", sync_job.name))
    
    # Set basic fields for testing
    if source_doc:
        target_doc.first_name = source_doc.customer_name


def after_start(sync_job, source_doc):
    """Hook called after job starts"""
    hook_calls.append(("after_start", sync_job.name))


def before_sync(sync_job, source_doc, target_doc):
    """Hook called before sync"""
    hook_calls.append(("before_sync", sync_job.name))


def after_sync(sync_job, source_doc, target_doc):
    """Hook called after sync"""
    hook_calls.append(("after_sync", sync_job.name))


def finished(sync_job, source_doc, target_doc):
    """Hook called when sync finishes"""
    hook_calls.append(("finished", sync_job.name))


def get_multiple_target_documents(sync_job, source_doc):
    """Get multiple target documents"""
    hook_calls.append(("get_multiple_target_documents", sync_job.name))
    
    # Return multiple targets to test relay hooks
    return [
        {
            "target_document_type": "Contact",
            "target_document_name": None,
            "operation": "insert",
            "context": {"batch": 1}
        },
        {
            "target_document_type": "Contact",
            "target_document_name": None,
            "operation": "insert",
            "context": {"batch": 2}
        }
    ]


def before_relay(sync_job, source_doc, targets):
    """Hook called before child jobs are queued"""
    hook_calls.append(("before_relay", sync_job.name, len(targets)))


def after_relay(sync_job, source_doc, child_jobs):
    """Hook called after child jobs are queued"""
    hook_calls.append(("after_relay", sync_job.name, len(child_jobs)))


def reset_hook_calls():
    """Reset hook calls for testing"""
    global hook_calls
    hook_calls = []


def get_hook_calls():
    """Get hook calls for testing"""
    return hook_calls
