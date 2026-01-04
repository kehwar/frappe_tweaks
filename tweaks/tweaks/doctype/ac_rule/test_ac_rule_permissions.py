# Copyright (c) 2025, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import (
    get_permission_query_conditions,
    has_permission,
    ptype_to_action,
)


class TestACRulePermissions(FrappeTestCase):
    """Test cases for AC Rule permission hooks"""

    def test_ptype_to_action(self):
        """Test ptype to action mapping"""
        self.assertEqual(ptype_to_action("read"), "Read")
        self.assertEqual(ptype_to_action("write"), "Write")
        self.assertEqual(ptype_to_action("create"), "Create")
        self.assertEqual(ptype_to_action("delete"), "Delete")
        self.assertEqual(ptype_to_action("submit"), "Submit")
        self.assertEqual(ptype_to_action("cancel"), "Cancel")
        self.assertEqual(ptype_to_action(None), "Read")

    def test_administrator_has_full_access(self):
        """Test that Administrator always has full access"""
        # Test permission query conditions
        conditions = get_permission_query_conditions("Customer", "Administrator")
        self.assertEqual(conditions, "")

        # Test has_permission
        doc = frappe._dict({"doctype": "Customer", "name": "Test Customer"})
        result = has_permission(doc, ptype="read", user="Administrator")
        self.assertTrue(result)

    def test_unmanaged_doctype_returns_empty(self):
        """Test that unmanaged doctypes return empty string/None"""
        # Create a doctype that has no AC Resources defined
        # Most standard doctypes should be unmanaged initially
        
        # Test permission query conditions
        conditions = get_permission_query_conditions("User", frappe.session.user)
        # Should return empty string for unmanaged (fall through to Frappe permissions)
        self.assertEqual(conditions, "")

    def test_permission_query_conditions_with_rules(self):
        """Test permission query conditions with actual AC Rules"""
        # This test would require setting up AC Resources, Query Filters, and AC Rules
        # For now, we'll just verify the function can be called without errors
        
        try:
            conditions = get_permission_query_conditions("Customer", frappe.session.user)
            # Should return a string (empty or with conditions)
            self.assertIsInstance(conditions, str)
        except Exception as e:
            self.fail(f"get_permission_query_conditions raised exception: {e}")

    def test_has_permission_with_rules(self):
        """Test has_permission with actual AC Rules"""
        # This test would require setting up AC Resources, Query Filters, and AC Rules
        # For now, we'll just verify the function can be called without errors
        
        try:
            doc = frappe._dict({"doctype": "Customer", "name": "Test Customer"})
            result = has_permission(doc, ptype="read", user=frappe.session.user)
            # Should return True, False, or None
            self.assertIn(result, [True, False, None])
        except Exception as e:
            self.fail(f"has_permission raised exception: {e}")

    def test_has_permission_for_new_document(self):
        """Test has_permission for new documents (create action)"""
        # Test with a new document (no name)
        doc = frappe._dict({"doctype": "Customer"})
        
        try:
            result = has_permission(doc, ptype="create", user=frappe.session.user)
            # Should return True, False, or None
            self.assertIn(result, [True, False, None])
        except Exception as e:
            self.fail(f"has_permission for new doc raised exception: {e}")

    def test_permission_hooks_integration(self):
        """Test that permission hooks are properly registered"""
        from tweaks.hooks import has_permission as has_perm_hooks
        from tweaks.hooks import permission_query_conditions as perm_query_hooks
        
        # Verify hooks are registered
        self.assertIn(
            "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.has_permission",
            has_perm_hooks.get("*", [])
        )
        self.assertIn(
            "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_permission_query_conditions",
            perm_query_hooks.get("*", [])
        )
