# Copyright (c) {year}, {app_publisher} and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# BYPASS MODE: Define this function to have full control
# def execute(sync_job, source_doc, filters, context):
# 	"""
# 	Execute sync job with full control
#
# 	Args:
# 		sync_job: Sync Job document
# 		source_doc: Source document
# 		filters: Dict of filters
# 		context: Dict of context data
#
# 	Returns:
# 		Dict with keys:
# 			target_doc: Target document (saved or unsaved)
# 			operation: "insert", "update", or "delete"
# 			diff: Dict of changes (optional)
# 	"""
# 	pass


# STANDARD MODE: Define these functions for framework-handled flow

# Optional: Return multiple targets (creates child jobs if > 1)
# def get_multiple_target_documents(sync_job, source_doc, create_missing, context):
# 	"""
# 	Get multiple target documents for this source
#
# 	Args:
# 		sync_job: Sync Job document
# 		source_doc: Source document
# 		create_missing: Whether to create missing targets
# 		context: Dict of context data
#
# 	Returns:
# 		List of dicts with keys:
# 			target_doc: Target document
# 			operation: "insert", "update", or "delete"
# 			context: Dict of context for this target (optional)
# 	"""
# 	return []


# Required: Get single target document
def get_target_document(sync_job, source_doc, create_missing, context):
    """
    Get target document for sync

    Args:
            sync_job: Sync Job document
            source_doc: Source document
            create_missing: Whether to create missing target
            context: Dict of context data

    Returns:
            Tuple of (target_doc, operation)
            operation: "insert", "update", or "delete"
    """
    # Example implementation
    target_doc = None
    operation = "insert"

    # Try to find existing target
    # target_name = frappe.db.get_value("Target DocType", {{{{"link_field": source_doc.name}}}})
    # if target_name:
    # 	target_doc = frappe.get_doc("Target DocType", target_name)
    # 	operation = "update"
    # elif create_missing:
    # 	target_doc = frappe.new_doc("Target DocType")
    # 	operation = "insert"

    return target_doc, operation


# Required: Get field mapping
def get_field_mapping(sync_job, source_doc, operation, context):
    """
    Get field mapping from source to target

    Args:
            sync_job: Sync Job document
            source_doc: Source document
            operation: "insert", "update", or "delete"
            context: Dict of context data

    Returns:
            Dict of field mappings
    """
    pass


# Optional: Update link field after sync
# def update_link_field(sync_job, source_doc, target_doc, operation, context):
# 	"""
# 	Update link field to establish bidirectional link
#
# 	Args:
# 		sync_job: Sync Job document
# 		source_doc: Source document
# 		target_doc: Target document (saved)
# 		operation: "insert", "update", or "delete"
# 		context: Dict of context data
# 	"""
# 	# Example: Update source with target link
# 	# source_doc.target_link = target_doc.name
# 	# source_doc.save(ignore_permissions=True)
# 	pass


# Optional: Before sync hook
# def before_sync(sync_job, source_doc, target_doc, operation, context):
# 	"""
# 	Hook called before sync
#
# 	Args:
# 		sync_job: Sync Job document
# 		source_doc: Source document
# 		target_doc: Target document (not yet saved)
# 		operation: "insert", "update", or "delete"
# 		context: Dict of context data
# 	"""
# 	pass


# Optional: After sync hook
# def after_sync(sync_job, source_doc, target_doc, operation, context):
# 	"""
# 	Hook called after sync
#
# 	Args:
# 		sync_job: Sync Job document
# 		source_doc: Source document
# 		target_doc: Target document (saved)
# 		operation: "insert", "update", or "delete"
# 		context: Dict of context data
# 	"""
# 	pass
