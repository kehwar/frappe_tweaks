# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

"""
Event Scripts Migration Report

This report extracts all Event Scripts currently configured in the system
for the purpose of migrating them to either Server Scripts or AC Rules.

Event Scripts are deprecated and will be removed in future versions.
This report helps identify which scripts need migration and provides
recommendations for the migration path.

Migration Paths:
1. Server Scripts: For general business logic that doesn't require fine-grained access control
2. AC Rules: For permission-related scripts (has_permission, has_field_permission)

The report shows all Event Scripts with their configuration, making it easier
to plan and execute the migration process.
"""

import frappe
from frappe import _


def execute(filters=None):
    """
    Execute the Event Scripts Migration report.
    
    Args:
        filters: Dictionary of filter values including:
            - disabled: Filter by disabled status (0, 1, or None for all)
            - document_type: Filter by specific document type
            - doctype_event: Filter by specific doctype event
            - migration_target: Filter by migration recommendation
    
    Returns:
        Tuple of (columns, data):
        - columns: List of column definitions
        - data: List of rows with event script data
    """
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data


def get_columns():
    """
    Define the columns for the report.
    
    Returns:
        List of column definitions with field names, labels, types, and widths
    """
    return [
        {
            "fieldname": "name",
            "label": _("ID"),
            "fieldtype": "Link",
            "options": "Event Script",
            "width": 120
        },
        {
            "fieldname": "title",
            "label": _("Title"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "disabled",
            "label": _("Disabled"),
            "fieldtype": "Check",
            "width": 80
        },
        {
            "fieldname": "priority",
            "label": _("Priority"),
            "fieldtype": "Int",
            "width": 80
        },
        {
            "fieldname": "document_type",
            "label": _("Document Type"),
            "fieldtype": "Link",
            "options": "DocType",
            "width": 150
        },
        {
            "fieldname": "document_type_group",
            "label": _("DocType Group"),
            "fieldtype": "Link",
            "options": "DocType Group",
            "width": 150
        },
        {
            "fieldname": "doctype_event",
            "label": _("DocType Event"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "action",
            "label": _("Action"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "workflow_action",
            "label": _("Workflow Action"),
            "fieldtype": "Link",
            "options": "Workflow Action Master",
            "width": 150
        },
        {
            "fieldname": "user_filter",
            "label": _("User Filter"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 120
        },
        {
            "fieldname": "user_group",
            "label": _("User Group"),
            "fieldtype": "Link",
            "options": "User Group",
            "width": 120
        },
        {
            "fieldname": "role",
            "label": _("Role"),
            "fieldtype": "Link",
            "options": "Role",
            "width": 120
        },
        {
            "fieldname": "role_profile",
            "label": _("Role Profile"),
            "fieldtype": "Link",
            "options": "Role Profile",
            "width": 120
        },
        {
            "fieldname": "script_preview",
            "label": _("Script Preview"),
            "fieldtype": "Data",
            "width": 300
        },
        {
            "fieldname": "parameter_count",
            "label": _("Parameters"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "migration_target",
            "label": _("Migration Target"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "migration_notes",
            "label": _("Migration Notes"),
            "fieldtype": "Data",
            "width": 300
        }
    ]


def get_data(filters=None):
    """
    Retrieve and process Event Script data for the report.
    
    Args:
        filters: Dictionary of filter values including:
            - disabled: Filter by disabled status (0, 1, or None for all)
            - document_type: Filter by specific document type
            - doctype_event: Filter by specific doctype event
            - migration_target: Filter by migration recommendation
    
    Returns:
        List of dictionaries, each representing a row in the report
    """
    # Build filter conditions
    filter_conditions = {}
    if filters:
        if filters.get("disabled") is not None:
            filter_conditions["disabled"] = filters.get("disabled")
        if filters.get("document_type"):
            filter_conditions["document_type"] = filters.get("document_type")
        if filters.get("doctype_event"):
            filter_conditions["doctype_event"] = filters.get("doctype_event")
    
    # Fetch all Event Scripts with relevant fields
    event_scripts = frappe.get_all(
        "Event Script",
        filters=filter_conditions,
        fields=[
            "name",
            "title",
            "disabled",
            "priority",
            "document_type",
            "document_type_group",
            "doctype_event",
            "action",
            "workflow_action",
            "user_filter",
            "user",
            "user_group",
            "role",
            "role_profile",
            "script"
        ],
        order_by="disabled asc, priority desc, title asc"
    )
    
    data = []
    
    for script in event_scripts:
        # Get parameter count
        parameter_count = frappe.db.count(
            "Event Script Parameter",
            {"parent": script.name}
        )
        
        # Create script preview (first 100 characters)
        script_preview = ""
        if script.script:
            script_preview = script.script[:100].replace("\n", " ").strip()
            if len(script.script) > 100:
                script_preview += "..."
        
        # Determine migration target and notes
        migration_target, migration_notes = get_migration_recommendation(script)
        
        data.append({
            "name": script.name,
            "title": script.title,
            "disabled": script.disabled,
            "priority": script.priority,
            "document_type": script.document_type,
            "document_type_group": script.document_type_group,
            "doctype_event": script.doctype_event,
            "action": script.action,
            "workflow_action": script.workflow_action,
            "user_filter": script.user_filter,
            "user": script.user,
            "user_group": script.user_group,
            "role": script.role,
            "role_profile": script.role_profile,
            "script_preview": script_preview,
            "parameter_count": parameter_count,
            "migration_target": migration_target,
            "migration_notes": migration_notes
        })
    
    # Apply post-processing filters
    if filters and filters.get("migration_target"):
        target_filter = filters.get("migration_target")
        data = [row for row in data if target_filter in row["migration_target"]]
    
    return data


def get_migration_recommendation(script):
    """
    Determine the recommended migration target for an Event Script.
    
    Args:
        script: Event Script document dictionary
    
    Returns:
        Tuple of (migration_target, migration_notes)
        - migration_target: "AC Rule" or "Server Script"
        - migration_notes: Additional guidance for migration
    """
    doctype_event = script.doctype_event
    
    # Permission-related events should migrate to AC Rules
    if doctype_event in ["has_permission", "has_field_permission"]:
        return (
            "AC Rule",
            "Migrate to AC Rule for fine-grained access control. "
            "Use Query Filters for principal and resource filtering."
        )
    
    # Transition events could use either, but AC Rules are recommended for consistency
    if doctype_event in ["before_transition", "after_transition", "transition_condition"]:
        return (
            "Server Script or AC Rule",
            "Consider AC Rule if access control is involved, otherwise Server Script. "
            "Workflow-specific logic may be better suited for Server Script."
        )
    
    # All other events should migrate to Server Scripts
    migration_notes = "Migrate to Server Script. "
    
    # Add specific guidance based on event type
    if doctype_event in ["validate", "before_save", "before_insert"]:
        migration_notes += "Use 'Before Save' or 'Before Insert' event type in Server Script."
    elif doctype_event in ["on_update", "after_insert"]:
        migration_notes += "Use 'After Save' or 'After Insert' event type in Server Script."
    elif doctype_event in ["on_submit", "on_cancel"]:
        migration_notes += "Use 'Before Submit' or 'Before Cancel' event type in Server Script."
    elif doctype_event in ["on_trash", "after_delete"]:
        migration_notes += "Use 'Before Delete' or 'After Delete' event type in Server Script."
    else:
        migration_notes += f"Map '{doctype_event}' event to appropriate Server Script event type."
    
    # Add note about user filters
    if script.user or script.user_group or script.role or script.role_profile:
        migration_notes += " NOTE: User/Role filtering will need to be implemented in the script logic."
    
    # Add note about parameters
    if script.get("parameter_count", 0) > 0:
        migration_notes += " NOTE: Event Script Parameters will need to be reimplemented."
    
    return "Server Script", migration_notes
