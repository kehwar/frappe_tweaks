# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _


def execute(filters=None):
    """Generate User Roles report showing users and their assigned roles"""
    columns, data = get_columns_and_data()
    return columns, data


def sanitize_fieldname(role_name):
    """Convert role name to valid fieldname by removing special characters"""
    # Replace spaces and special chars with underscores, convert to lowercase
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', role_name).lower()
    # Remove leading/trailing underscores and collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = 'role_' + sanitized
    return sanitized or 'role_unnamed'


def get_columns_and_data():
    """Get columns and data for the report"""
    
    # Step 1: Get all enabled users with their role profiles
    users = frappe.db.sql(
        """
        SELECT 
            name,
            full_name,
            role_profile_name
        FROM `tabUser`
        WHERE enabled = 1
        AND user_type = 'System User'
        AND name NOT IN ('Administrator', 'Guest')
        ORDER BY full_name, name
        """,
        as_dict=True,
    )
    
    if not users:
        return get_empty_columns(), []
    
    # Step 2: Get all role assignments for enabled users
    user_names = [user.name for user in users]
    
    # Use parameterized query with IN clause
    placeholders = ", ".join(["%s"] * len(user_names))
    query = """
        SELECT 
            hr.parent as user,
            hr.role
        FROM `tabHas Role` hr
        WHERE hr.parenttype = 'User'
        AND hr.parent IN ({})
        """.format(placeholders)
    
    role_assignments = frappe.db.sql(query, tuple(user_names), as_dict=True)
    
    # Step 3: Build user-role mapping
    user_roles = {}
    for assignment in role_assignments:
        if assignment.user not in user_roles:
            user_roles[assignment.user] = set()
        user_roles[assignment.user].add(assignment.role)
    
    # If no role assignments found, return empty result
    if not user_roles:
        return get_empty_columns(), []
    
    # Step 4: Count users per role (only for roles with at least one enabled user)
    role_counts = {}
    for user_role_set in user_roles.values():
        for role in user_role_set:
            role_counts[role] = role_counts.get(role, 0) + 1
    
    # Step 5: Sort roles by user count (descending)
    sorted_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)
    sorted_role_names = [role for role, count in sorted_roles]
    
    # Step 6: Build columns
    columns = [
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 200,
        },
        {
            "fieldname": "full_name",
            "label": _("Full Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "role_profile",
            "label": _("Role Profile"),
            "fieldtype": "Link",
            "options": "Role Profile",
            "width": 150,
        },
    ]
    
    # Add one column per role
    for role in sorted_role_names:
        columns.append(
            {
                "fieldname": f"role_{sanitize_fieldname(role)}",
                "label": _(role),
                "fieldtype": "Check",
                "width": 100,
            }
        )
    
    # Step 7: Build data rows
    data = []
    for user in users:
        row = {
            "user": user.name,
            "full_name": user.full_name or "",
            "role_profile": user.role_profile_name or "",
        }
        
        # Add role assignments
        user_role_set = user_roles.get(user.name, set())
        for role in sorted_role_names:
            row[f"role_{sanitize_fieldname(role)}"] = 1 if role in user_role_set else 0
        
        data.append(row)
    
    return columns, data


def get_empty_columns():
    """Return basic columns when no data is available"""
    return [
        {
            "fieldname": "user",
            "label": _("User"),
            "fieldtype": "Link",
            "options": "User",
            "width": 200,
        },
        {
            "fieldname": "full_name",
            "label": _("Full Name"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "role_profile",
            "label": _("Role Profile"),
            "fieldtype": "Link",
            "options": "Role Profile",
            "width": 150,
        },
    ]
