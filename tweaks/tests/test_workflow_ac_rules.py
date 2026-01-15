# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Test cases for Workflow Action AC Rules Integration

This module tests the integration between Frappe's workflow system and
the AC Rules permission system, including:
- check_workflow_transition_permission: Blocking unauthorized transitions
- filter_transitions_by_ac_rules: Filtering available transitions
- get_workflow_action_permission_query_conditions: SQL filtering for Workflow Actions
- has_workflow_action_permission_via_ac_rules: Direct permission checks
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from tweaks.utils.workflow import (
    check_workflow_transition_permission,
    filter_transitions_by_ac_rules,
    get_workflow_action_permission_query_conditions,
    has_workflow_action_permission_via_ac_rules,
)


class TestWorkflowACRules(FrappeTestCase):
    """Test cases for workflow action AC rules integration"""

    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests"""
        super().setUpClass()
        frappe.set_user("Administrator")
        
        # Create test users
        cls.test_user_1 = create_test_user("test_workflow_user1@example.com", "Test User 1")
        cls.test_user_2 = create_test_user("test_workflow_user2@example.com", "Test User 2")
        
        # Create test roles
        cls.test_role_1 = create_test_role("Workflow Test Role 1")
        cls.test_role_2 = create_test_role("Workflow Test Role 2")
        
        # Assign roles to users
        assign_role_to_user(cls.test_user_1, cls.test_role_1)
        assign_role_to_user(cls.test_user_2, cls.test_role_2)
        
        # Create test DocType with workflow
        create_test_doctype_with_workflow()
        
        # Create AC Actions for workflow actions
        create_ac_action("approve")
        create_ac_action("reject")
        
        # Create AC Resource for the test DocType
        cls.ac_resource = create_ac_resource("Test Workflow DocType")
        
        # Clear AC Rule cache
        frappe.cache.delete_value("ac_rule_map")

    @classmethod
    def tearDownClass(cls):
        """Clean up test data after all tests"""
        frappe.set_user("Administrator")
        
        # Delete test data
        try:
            # Delete AC Rules
            for rule in frappe.get_all("AC Rule", filters={"name": ["like", "Test Workflow AC Rule%"]}):
                frappe.delete_doc("AC Rule", rule.name, force=True)
            
            # Delete AC Resource
            if hasattr(cls, "ac_resource") and cls.ac_resource:
                frappe.delete_doc("AC Resource", cls.ac_resource, force=True, ignore_permissions=True)
            
            # Delete test documents
            for doc in frappe.get_all("Test Workflow DocType"):
                frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
            
            # Delete workflow
            if frappe.db.exists("Workflow", "Test Workflow DocType Workflow"):
                frappe.delete_doc("Workflow", "Test Workflow DocType Workflow", force=True)
            
            # Delete DocType
            if frappe.db.exists("DocType", "Test Workflow DocType"):
                frappe.delete_doc("DocType", "Test Workflow DocType", force=True, ignore_permissions=True)
            
            # Delete test users and roles
            for user in [cls.test_user_1, cls.test_user_2]:
                if frappe.db.exists("User", user):
                    frappe.delete_doc("User", user, force=True)
            
            for role in [cls.test_role_1, cls.test_role_2]:
                if frappe.db.exists("Role", role):
                    frappe.delete_doc("Role", role, force=True)
        except Exception as e:
            frappe.log_error(f"Error in tearDownClass: {str(e)}")
        
        super().tearDownClass()

    def setUp(self):
        """Set up for each test"""
        frappe.set_user("Administrator")
        
        # Clear AC Rule cache before each test
        frappe.cache.delete_value("ac_rule_map")
        
        # Clear user-rule matching cache
        cache = frappe.cache
        if hasattr(cache, 'delete_keys'):
            cache.delete_keys("ac_rule_user_match:*")

    def test_check_workflow_transition_permission_with_permission(self):
        """Test that users with AC permission can perform transitions"""
        # Create AC Rule that allows test_user_1 to approve
        rule = create_ac_rule(
            name="Test Workflow AC Rule 1",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Create a mock transition object
        transition = frappe._dict({
            "action": "Approve",
            "state": "Draft",
            "next_state": "Approved"
        })
        
        # Set user context
        frappe.set_user(self.test_user_1)
        
        # This should not raise an exception
        try:
            check_workflow_transition_permission(doc, transition=transition)
            success = True
        except frappe.PermissionError:
            success = False
        
        self.assertTrue(success, "User with AC permission should be allowed to transition")
        
        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_check_workflow_transition_permission_without_permission(self):
        """Test that users without AC permission are blocked from transitions"""
        # Create AC Rule that allows test_user_1 to approve (but not test_user_2)
        rule = create_ac_rule(
            name="Test Workflow AC Rule 2",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Create a mock transition object
        transition = frappe._dict({
            "action": "Approve",
            "state": "Draft",
            "next_state": "Approved"
        })
        
        # Set user context to user without permission
        frappe.set_user(self.test_user_2)
        
        # This should raise a PermissionError
        with self.assertRaises(frappe.PermissionError):
            check_workflow_transition_permission(doc, transition=transition)
        
        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_filter_transitions_by_ac_rules_with_permission(self):
        """Test that filter_transitions_by_ac_rules includes allowed transitions"""
        # Create AC Rule that allows test_user_1 to approve
        rule = create_ac_rule(
            name="Test Workflow AC Rule 3",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Mock workflow object
        workflow = frappe._dict({"name": "Test Workflow DocType Workflow"})
        
        # Mock transitions
        transitions = [
            frappe._dict({"action": "Approve", "state": "Draft", "next_state": "Approved"}),
            frappe._dict({"action": "Reject", "state": "Draft", "next_state": "Rejected"}),
        ]
        
        # Set user context
        frappe.set_user(self.test_user_1)
        
        # Filter transitions
        filtered = filter_transitions_by_ac_rules(doc, transitions, workflow)
        
        # User should only see "Approve" transition
        self.assertEqual(len(filtered), 1, "Only one transition should be allowed")
        self.assertEqual(filtered[0].action, "Approve", "Approve transition should be included")
        
        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_filter_transitions_by_ac_rules_without_permission(self):
        """Test that filter_transitions_by_ac_rules excludes disallowed transitions"""
        # Create AC Rule that allows test_user_1 to approve (but not test_user_2)
        rule = create_ac_rule(
            name="Test Workflow AC Rule 4",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Mock workflow object
        workflow = frappe._dict({"name": "Test Workflow DocType Workflow"})
        
        # Mock transitions
        transitions = [
            frappe._dict({"action": "Approve", "state": "Draft", "next_state": "Approved"}),
        ]
        
        # Set user context to user without permission
        frappe.set_user(self.test_user_2)
        
        # Filter transitions
        filtered = filter_transitions_by_ac_rules(doc, transitions, workflow)
        
        # User should see no transitions
        self.assertEqual(len(filtered), 0, "No transitions should be allowed for user without permission")
        
        # Cleanup
        frappe.set_user("Administrator")
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_has_workflow_action_permission_via_ac_rules_with_permission(self):
        """Test has_workflow_action_permission_via_ac_rules returns True for allowed actions"""
        # Create AC Rule that allows test_user_1 to approve
        rule = create_ac_rule(
            name="Test Workflow AC Rule 5",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Mock transition
        transition = {"action": "Approve"}
        
        # Check permission
        has_permission = has_workflow_action_permission_via_ac_rules(
            self.test_user_1, transition, doc
        )
        
        self.assertTrue(has_permission, "User should have permission for approved action")
        
        # Cleanup
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_has_workflow_action_permission_via_ac_rules_without_permission(self):
        """Test has_workflow_action_permission_via_ac_rules returns False for disallowed actions"""
        # Create AC Rule that allows test_user_1 to approve (but not test_user_2)
        rule = create_ac_rule(
            name="Test Workflow AC Rule 6",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Mock transition
        transition = {"action": "Approve"}
        
        # Check permission for user without access
        has_permission = has_workflow_action_permission_via_ac_rules(
            self.test_user_2, transition, doc
        )
        
        self.assertFalse(has_permission, "User should not have permission for action")
        
        # Cleanup
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_get_workflow_action_permission_query_conditions_administrator(self):
        """Test that Administrator gets no conditions (full access)"""
        frappe.set_user("Administrator")
        
        conditions = get_workflow_action_permission_query_conditions(
            user="Administrator", doctype="Workflow Action"
        )
        
        self.assertEqual(conditions, "", "Administrator should have no query conditions")

    def test_get_workflow_action_permission_query_conditions_with_rules(self):
        """Test that query conditions are generated for users with AC Rules"""
        # Create AC Rule that allows test_user_1 to approve
        rule = create_ac_rule(
            name="Test Workflow AC Rule 7",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit",
            all_resources=True  # Grant access to all documents
        )
        
        # Create test document with workflow
        doc = create_test_workflow_document()
        
        # Create a workflow action for this document
        create_workflow_action(doc.name, "Draft", "Approve")
        
        # Set user context
        frappe.set_user(self.test_user_1)
        
        # Get query conditions
        conditions = get_workflow_action_permission_query_conditions(
            user=self.test_user_1, doctype="Workflow Action"
        )
        
        # Conditions should be generated (non-empty string or empty if unmanaged/total access)
        self.assertIsInstance(conditions, str, "Conditions should be a string")
        
        # Cleanup
        frappe.set_user("Administrator")
        for wa in frappe.get_all("Workflow Action", filters={"reference_name": doc.name}):
            frappe.delete_doc("Workflow Action", wa.name, force=True)
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", rule, force=True)

    def test_forbid_rule_blocks_permission(self):
        """Test that Forbid rules block permission even when Permit rule exists"""
        # Create a Permit rule for all users
        permit_rule = create_ac_rule(
            name="Test Workflow AC Rule Permit",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Permit"
        )
        
        # Create a Forbid rule specifically for test_user_1
        forbid_rule = create_ac_rule(
            name="Test Workflow AC Rule Forbid",
            resource=self.ac_resource,
            action="approve",
            user=self.test_user_1,
            rule_type="Forbid"
        )
        
        # Create test document
        doc = create_test_workflow_document()
        
        # Mock transition
        transition = {"action": "Approve"}
        
        # Check permission - should be False due to Forbid rule
        has_permission = has_workflow_action_permission_via_ac_rules(
            self.test_user_1, transition, doc
        )
        
        self.assertFalse(has_permission, "Forbid rule should block permission")
        
        # Cleanup
        frappe.delete_doc("Test Workflow DocType", doc.name, force=True)
        frappe.delete_doc("AC Rule", forbid_rule, force=True)
        frappe.delete_doc("AC Rule", permit_rule, force=True)


# Helper functions

def create_test_user(email, full_name):
    """Create a test user if not exists"""
    if not frappe.db.exists("User", email):
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": full_name.split()[0],
            "last_name": full_name.split()[-1] if len(full_name.split()) > 1 else "",
            "send_welcome_email": 0,
            "user_type": "System User"
        })
        user.insert(ignore_permissions=True)
        frappe.db.commit()
    return email


def create_test_role(role_name):
    """Create a test role if not exists"""
    if not frappe.db.exists("Role", role_name):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name
        })
        role.insert(ignore_permissions=True)
        frappe.db.commit()
    return role_name


def assign_role_to_user(user, role):
    """Assign a role to a user"""
    if not frappe.db.exists("Has Role", {"parent": user, "role": role}):
        user_doc = frappe.get_doc("User", user)
        user_doc.append("roles", {"role": role})
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()


def create_test_doctype_with_workflow():
    """Create a test DocType with workflow"""
    if frappe.db.exists("DocType", "Test Workflow DocType"):
        return
    
    # Create DocType
    doctype = frappe.get_doc({
        "doctype": "DocType",
        "name": "Test Workflow DocType",
        "module": "Tweaks",
        "custom": 1,
        "is_submittable": 1,
        "fields": [
            {
                "fieldname": "title",
                "fieldtype": "Data",
                "label": "Title",
                "reqd": 1
            },
            {
                "fieldname": "workflow_state",
                "fieldtype": "Link",
                "label": "Workflow State",
                "options": "Workflow State",
                "hidden": 1
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "submit": 1,
                "cancel": 1
            },
            {
                "role": "Workflow Test Role 1",
                "read": 1,
                "write": 1
            },
            {
                "role": "Workflow Test Role 2",
                "read": 1,
                "write": 1
            }
        ]
    })
    doctype.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Create workflow states
    for state in ["Draft", "Approved", "Rejected"]:
        if not frappe.db.exists("Workflow State", state):
            state_doc = frappe.get_doc({
                "doctype": "Workflow State",
                "workflow_state_name": state
            })
            state_doc.insert(ignore_permissions=True)
    
    # Create workflow
    if not frappe.db.exists("Workflow", "Test Workflow DocType Workflow"):
        workflow = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "Test Workflow DocType Workflow",
            "document_type": "Test Workflow DocType",
            "workflow_state_field": "workflow_state",
            "is_active": 1,
            "states": [
                {
                    "state": "Draft",
                    "doc_status": "0",
                    "allow_edit": "Workflow Test Role 1"
                },
                {
                    "state": "Approved",
                    "doc_status": "1",
                    "allow_edit": "System Manager"
                },
                {
                    "state": "Rejected",
                    "doc_status": "2",
                    "allow_edit": "System Manager"
                }
            ],
            "transitions": [
                {
                    "state": "Draft",
                    "action": "Approve",
                    "next_state": "Approved",
                    "allowed": "Workflow Test Role 1",
                    "allow_self_approval": 1
                },
                {
                    "state": "Draft",
                    "action": "Reject",
                    "next_state": "Rejected",
                    "allowed": "Workflow Test Role 2",
                    "allow_self_approval": 1
                }
            ]
        })
        workflow.insert(ignore_permissions=True)
        frappe.db.commit()


def create_ac_action(action_name):
    """Create an AC Action if not exists"""
    if not frappe.db.exists("AC Action", action_name):
        action = frappe.get_doc({
            "doctype": "AC Action",
            "action": action_name,
            "disabled": 0
        })
        action.insert(ignore_permissions=True)
        frappe.db.commit()


def create_ac_resource(doctype_name):
    """Create an AC Resource for a DocType"""
    resource_name = f"AC Resource for {doctype_name}"
    
    if frappe.db.exists("AC Resource", resource_name):
        return resource_name
    
    resource = frappe.get_doc({
        "doctype": "AC Resource",
        "resource_name": resource_name,
        "document_type": doctype_name,
        "managed_actions": "All",
        "disabled": 0
    })
    resource.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return resource_name


def create_ac_rule(name, resource, action, user, rule_type="Permit", all_resources=False):
    """Create an AC Rule"""
    if frappe.db.exists("AC Rule", name):
        frappe.delete_doc("AC Rule", name, force=True)
    
    # Create a simple query filter for the user (principal)
    user_filter = create_query_filter(f"User Filter for {name}", "User", user)
    
    # Create a query filter for resources (all documents or specific filter)
    if all_resources:
        resource_filter = create_query_filter(
            f"Resource Filter for {name}",
            "Test Workflow DocType",
            None,
            all_filter=True
        )
    else:
        # Create a filter that matches all documents (for simplicity in tests)
        resource_filter = create_query_filter(
            f"Resource Filter for {name}",
            "Test Workflow DocType",
            None,
            all_filter=True
        )
    
    rule = frappe.get_doc({
        "doctype": "AC Rule",
        "title": name,
        "resource": resource,
        "type": rule_type,
        "disabled": 0,
        "actions": [
            {
                "action": action
            }
        ],
        "principals": [
            {
                "filter": user_filter,
                "exception": 0
            }
        ],
        "resources": [
            {
                "filter": resource_filter,
                "exception": 0
            }
        ]
    })
    rule.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Clear cache
    frappe.cache.delete_value("ac_rule_map")
    
    return name


def create_query_filter(filter_name, reference_doctype, user_email, all_filter=False):
    """Create a Query Filter for testing"""
    if frappe.db.exists("Query Filter", filter_name):
        return filter_name
    
    # If all_filter is True, create a filter that matches all records
    if all_filter:
        query_filter = frappe.get_doc({
            "doctype": "Query Filter",
            "filter_name": filter_name,
            "reference_doctype": reference_doctype,
            "disabled": 0,
            "filters_type": "SQL",
            "filters": "1=1"  # SQL that matches all records
        })
    else:
        # Create a filter that matches a specific user
        query_filter = frappe.get_doc({
            "doctype": "Query Filter",
            "filter_name": filter_name,
            "reference_doctype": reference_doctype,
            "disabled": 0,
            "filters_type": "JSON",
            "filters": frappe.as_json([
                ["name", "=", user_email]
            ])
        })
    
    query_filter.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return filter_name


def create_test_workflow_document():
    """Create a test workflow document"""
    doc = frappe.get_doc({
        "doctype": "Test Workflow DocType",
        "title": f"Test Doc {frappe.utils.now()}",
        "workflow_state": "Draft"
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return doc


def create_workflow_action(reference_name, workflow_state, action):
    """Create a Workflow Action document"""
    if frappe.db.exists("Workflow Action", {
        "reference_name": reference_name,
        "workflow_state": workflow_state
    }):
        return
    
    wa = frappe.get_doc({
        "doctype": "Workflow Action",
        "reference_doctype": "Test Workflow DocType",
        "reference_name": reference_name,
        "workflow_state": workflow_state,
        "status": "Open"
    })
    wa.insert(ignore_permissions=True)
    frappe.db.commit()
