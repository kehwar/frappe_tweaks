# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from tweaks.tweaks.report.ac_resource_rules.ac_resource_rules import (
    execute,
    build_filter_columns,
    get_user_actions_for_filter_column,
    get_users,
)


class TestACResourceRulesReport(FrappeTestCase):
    """Test cases for AC Resource Rules report"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.create_test_data()

    @classmethod
    def create_test_data(cls):
        """Create test data for AC Resource Rules report tests"""
        # Ensure standard AC Actions exist
        from tweaks.tweaks.doctype.ac_action.ac_action import insert_standard_actions
        insert_standard_actions()
        frappe.db.commit()
        
        # Initialize class variables
        cls.test_users = []
        cls.test_filters = {}
        cls.test_resource = None
        
        # Create test users
        for i in range(3):
            user_email = f"test_user_{i}@example.com"
            if not frappe.db.exists("User", user_email):
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": user_email,
                    "first_name": f"Test User {i}",
                    "enabled": 1,
                    "send_welcome_email": 0
                })
                user.insert(ignore_permissions=True)
                cls.test_users.append(user_email)
            else:
                cls.test_users.append(user_email)

        # Create test AC Resource
        if not frappe.db.exists("AC Resource", "Test Resource"):
            resource = frappe.get_doc({
                "doctype": "AC Resource",
                "title": "Test Resource",
                "type": "DocType",
                "document_type": "User",
                "managed_actions": "All Actions"
            })
            resource.insert(ignore_permissions=True)
            cls.test_resource = resource.name
        else:
            cls.test_resource = "Test Resource"

        # Create test Query Filters
        
        # Allow filter 1
        if not frappe.db.exists("Query Filter", {"filter_name": "Test Allow Filter 1"}):
            allow_filter_1 = frappe.get_doc({
                "doctype": "Query Filter",
                "filter_name": "Test Allow Filter 1",
                "reference_doctype": "User",
                "filters_type": "SQL",
                "filters": f"email = '{cls.test_users[0]}'"
            })
            allow_filter_1.insert(ignore_permissions=True)
            cls.test_filters["allow1"] = allow_filter_1.name
        else:
            cls.test_filters["allow1"] = frappe.db.get_value(
                "Query Filter", {"filter_name": "Test Allow Filter 1"}, "name"
            )

        # Allow filter 2
        if not frappe.db.exists("Query Filter", {"filter_name": "Test Allow Filter 2"}):
            allow_filter_2 = frappe.get_doc({
                "doctype": "Query Filter",
                "filter_name": "Test Allow Filter 2",
                "reference_doctype": "User",
                "filters_type": "SQL",
                "filters": f"email IN ('{cls.test_users[0]}', '{cls.test_users[1]}')"
            })
            allow_filter_2.insert(ignore_permissions=True)
            cls.test_filters["allow2"] = allow_filter_2.name
        else:
            cls.test_filters["allow2"] = frappe.db.get_value(
                "Query Filter", {"filter_name": "Test Allow Filter 2"}, "name"
            )

        # Forbid filter
        if not frappe.db.exists("Query Filter", {"filter_name": "Test Forbid Filter"}):
            forbid_filter = frappe.get_doc({
                "doctype": "Query Filter",
                "filter_name": "Test Forbid Filter",
                "reference_doctype": "User",
                "filters_type": "SQL",
                "filters": f"email = '{cls.test_users[1]}'"
            })
            forbid_filter.insert(ignore_permissions=True)
            cls.test_filters["forbid1"] = forbid_filter.name
        else:
            cls.test_filters["forbid1"] = frappe.db.get_value(
                "Query Filter", {"filter_name": "Test Forbid Filter"}, "name"
            )

        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        """Clean up test data"""
        # Clean up in reverse order due to dependencies
        if hasattr(cls, 'test_filters'):
            for filter_name in cls.test_filters.values():
                if frappe.db.exists("Query Filter", filter_name):
                    frappe.delete_doc("Query Filter", filter_name, force=1, ignore_permissions=True)
        
        if hasattr(cls, 'test_resource') and cls.test_resource:
            if frappe.db.exists("AC Resource", cls.test_resource):
                frappe.delete_doc("AC Resource", cls.test_resource, force=1, ignore_permissions=True)
        
        if hasattr(cls, 'test_users'):
            for user_email in cls.test_users:
                if frappe.db.exists("User", user_email):
                    frappe.delete_doc("User", user_email, force=1, ignore_permissions=True)
        
        frappe.db.commit()
        super().tearDownClass()

    def test_execute_without_filters(self):
        """Test execute function returns empty when no filters provided"""
        columns, data = execute()
        self.assertEqual(columns, [])
        self.assertEqual(data, [])

    def test_execute_without_resource(self):
        """Test execute function returns empty when resource filter is missing"""
        columns, data = execute({"query_filter": "some_filter"})
        self.assertEqual(columns, [])
        self.assertEqual(data, [])

    def test_execute_with_nonexistent_resource(self):
        """Test execute function with non-existent resource"""
        try:
            columns, data = execute({"resource": "Nonexistent Resource"})
            # Should either return empty or raise an error
            self.assertTrue(isinstance(columns, list))
            self.assertTrue(isinstance(data, list))
        except frappe.DoesNotExistError:
            # This is also acceptable behavior
            pass

    def test_build_filter_columns_basic(self):
        """Test building filter columns from AC Rules"""
        # Create a test AC Rule
        rule = frappe.get_doc({
            "doctype": "AC Rule",
            "title": "Test Rule Basic",
            "type": "Permit",
            "resource": self.test_resource,
            "principals": [
                {"filter": self.test_filters["allow1"], "exception": 0}
            ],
            "actions": [
                {"action": "Read"}
            ]
        })
        rule.insert(ignore_permissions=True)

        try:
            # Get rules for testing
            ac_rules = frappe.get_all(
                "AC Rule",
                filters={"resource": self.test_resource, "disabled": 0},
                fields=["name", "title", "type", "valid_from", "valid_upto"]
            )

            columns = build_filter_columns(ac_rules)
            
            # Should have at least one column
            self.assertGreater(len(columns), 0)
            
            # Each column should have required fields
            for col in columns:
                self.assertIn("fieldname", col)
                self.assertIn("label", col)
                self.assertIn("allowed_filters", col)
                self.assertIn("denied_filters", col)
                self.assertIn("rules", col)

        finally:
            frappe.delete_doc("AC Rule", rule.name, force=1, ignore_permissions=True)
            frappe.db.commit()

    def test_build_filter_columns_with_exceptions(self):
        """Test building filter columns with exception filters"""
        # Create a test AC Rule with exceptions
        rule = frappe.get_doc({
            "doctype": "AC Rule",
            "title": "Test Rule With Exceptions",
            "type": "Permit",
            "resource": self.test_resource,
            "principals": [
                {"filter": self.test_filters["allow2"], "exception": 0},
                {"filter": self.test_filters["forbid1"], "exception": 1}
            ],
            "actions": [
                {"action": "Read"},
                {"action": "Write"}
            ]
        })
        rule.insert(ignore_permissions=True)

        try:
            ac_rules = frappe.get_all(
                "AC Rule",
                filters={"resource": self.test_resource, "disabled": 0},
                fields=["name", "title", "type", "valid_from", "valid_upto"]
            )

            columns = build_filter_columns(ac_rules)
            
            # Should have columns
            self.assertGreater(len(columns), 0)
            
            # Find column with denied filters
            columns_with_denied = [c for c in columns if c["denied_filters"]]
            self.assertGreater(len(columns_with_denied), 0)
            
            # Check that denied filters are included
            for col in columns_with_denied:
                self.assertIn("⚠️", col["label"])

        finally:
            frappe.delete_doc("AC Rule", rule.name, force=1, ignore_permissions=True)
            frappe.db.commit()

    def test_emoji_in_column_labels(self):
        """Test that column labels contain appropriate emojis"""
        # Create test rules
        permit_rule = frappe.get_doc({
            "doctype": "AC Rule",
            "title": "Test Permit Rule",
            "type": "Permit",
            "resource": self.test_resource,
            "principals": [
                {"filter": self.test_filters["allow1"], "exception": 0}
            ],
            "actions": [
                {"action": "Read"}
            ]
        })
        permit_rule.insert(ignore_permissions=True)

        try:
            ac_rules = frappe.get_all(
                "AC Rule",
                filters={"resource": self.test_resource, "disabled": 0},
                fields=["name", "title", "type", "valid_from", "valid_upto"]
            )

            columns = build_filter_columns(ac_rules)
            
            # Check for Permit emoji (✅) or Forbid emoji (🚫)
            emoji_found = False
            for col in columns:
                if "✅" in col["label"] or "🚫" in col["label"]:
                    emoji_found = True
                    break
            
            self.assertTrue(emoji_found, "Column labels should contain emoji indicators")

        finally:
            frappe.delete_doc("AC Rule", permit_rule.name, force=1, ignore_permissions=True)
            frappe.db.commit()

    def test_get_users_without_filter(self):
        """Test getting all enabled users"""
        users = get_users()
        
        # Should return a list
        self.assertIsInstance(users, list)
        
        # Should contain at least the test users
        for test_user in self.test_users:
            self.assertIn(test_user, users)

    def test_get_users_with_invalid_filter_type(self):
        """Test that invalid filter types raise an error"""
        # Create a query filter with invalid reference doctype
        invalid_filter = frappe.get_doc({
            "doctype": "Query Filter",
            "filter_name": "Test Invalid Filter",
            "reference_doctype": "DocType",  # Not User-related
            "filters_type": "SQL",
            "filters": "1=1"
        })
        invalid_filter.insert(ignore_permissions=True)

        try:
            with self.assertRaises(frappe.exceptions.ValidationError):
                get_users(invalid_filter.name)
        finally:
            frappe.delete_doc("Query Filter", invalid_filter.name, force=1, ignore_permissions=True)
            frappe.db.commit()

    def test_action_aggregation(self):
        """Test that actions from multiple rules are aggregated correctly"""
        # Create two rules with the same filter but different actions
        rule1 = frappe.get_doc({
            "doctype": "AC Rule",
            "title": "Test Rule 1",
            "type": "Permit",
            "resource": self.test_resource,
            "principals": [
                {"filter": self.test_filters["allow1"], "exception": 0}
            ],
            "actions": [
                {"action": "Read"}
            ]
        })
        rule1.insert(ignore_permissions=True)

        rule2 = frappe.get_doc({
            "doctype": "AC Rule",
            "title": "Test Rule 2",
            "type": "Permit",
            "resource": self.test_resource,
            "principals": [
                {"filter": self.test_filters["allow1"], "exception": 0}
            ],
            "actions": [
                {"action": "Write"}
            ]
        })
        rule2.insert(ignore_permissions=True)

        try:
            ac_rules = frappe.get_all(
                "AC Rule",
                filters={"resource": self.test_resource, "disabled": 0},
                fields=["name", "title", "type", "valid_from", "valid_upto"]
            )

            columns = build_filter_columns(ac_rules)
            
            # Find the column for allow1
            allow1_cols = [c for c in columns if self.test_filters["allow1"] in c["allowed_filters"]]
            self.assertGreater(len(allow1_cols), 0)
            
            # Check that the column has multiple rules
            for col in allow1_cols:
                if not col["denied_filters"]:  # Only check columns without exceptions
                    self.assertGreaterEqual(len(col["rules"]), 2)

        finally:
            frappe.delete_doc("AC Rule", rule1.name, force=1, ignore_permissions=True)
            frappe.delete_doc("AC Rule", rule2.name, force=1, ignore_permissions=True)
            frappe.db.commit()

    def test_column_fieldnames_are_unique(self):
        """Test that generated column fieldnames are unique"""
        # Create multiple rules
        rules = []
        for i in range(3):
            rule = frappe.get_doc({
                "doctype": "AC Rule",
                "title": f"Test Rule {i}",
                "type": "Permit",
                "resource": self.test_resource,
                "principals": [
                    {"filter": self.test_filters["allow1"], "exception": 0}
                ],
                "actions": [
                    {"action": "Read"}
                ]
            })
            rule.insert(ignore_permissions=True)
            rules.append(rule)

        try:
            ac_rules = frappe.get_all(
                "AC Rule",
                filters={"resource": self.test_resource, "disabled": 0},
                fields=["name", "title", "type", "valid_from", "valid_upto"]
            )

            columns = build_filter_columns(ac_rules)
            
            # Extract fieldnames
            fieldnames = [col["fieldname"] for col in columns]
            
            # Check that all fieldnames are unique
            self.assertEqual(len(fieldnames), len(set(fieldnames)))

        finally:
            for rule in rules:
                frappe.delete_doc("AC Rule", rule.name, force=1, ignore_permissions=True)
            frappe.db.commit()
