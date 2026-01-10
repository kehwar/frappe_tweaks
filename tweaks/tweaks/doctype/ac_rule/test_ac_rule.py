# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestACRule(FrappeTestCase):
    """Test cases for AC Rule helper functions"""

    def setUp(self):
        """Set up test data"""
        # Create a simple AC Rule document for testing
        # Note: We're not saving to DB, just testing the logic
        self.rule = frappe.new_doc("AC Rule")
        self.rule.title = "Test Rule"
        self.rule.type = "Permit"

    def test_get_distinct_query_filters_with_multiple_non_exceptions(self):
        """Test with multiple non-exception filters and multiple exception filters"""
        # Add principals: allow1, allow2, allow3, forbid1, forbid2
        self.rule.append("principals", {"filter": "allow1", "exception": 0})
        self.rule.append("principals", {"filter": "allow2", "exception": 0})
        self.rule.append("principals", {"filter": "allow3", "exception": 0})
        self.rule.append("principals", {"filter": "forbid1", "exception": 1})
        self.rule.append("principals", {"filter": "forbid2", "exception": 1})

        result = self.rule.get_distinct_principal_query_filters()

        # Should have 3 tuples (one for each non-exception)
        self.assertEqual(len(result), 3)

        # Each tuple should have: (rule_type, filter_name, (exception_filters))
        self.assertEqual(result[0], ("Permit", "allow1", ("forbid1", "forbid2")))
        self.assertEqual(result[1], ("Permit", "allow2", ("forbid1", "forbid2")))
        self.assertEqual(result[2], ("Permit", "allow3", ("forbid1", "forbid2")))

    def test_get_distinct_query_filters_with_no_exceptions(self):
        """Test with only non-exception filters"""
        # Add principals: allow1, allow2
        self.rule.append("principals", {"filter": "allow1", "exception": 0})
        self.rule.append("principals", {"filter": "allow2", "exception": 0})

        result = self.rule.get_distinct_principal_query_filters()

        # Should have 2 tuples with empty exception tuple
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("Permit", "allow1", ()))
        self.assertEqual(result[1], ("Permit", "allow2", ()))

    def test_get_distinct_query_filters_forbid_type(self):
        """Test with Forbid rule type"""
        self.rule.type = "Forbid"
        self.rule.append("principals", {"filter": "deny1", "exception": 0})
        self.rule.append("principals", {"filter": "deny2", "exception": 0})
        self.rule.append("principals", {"filter": "except1", "exception": 1})

        result = self.rule.get_distinct_principal_query_filters()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("Forbid", "deny1", ("except1",)))
        self.assertEqual(result[1], ("Forbid", "deny2", ("except1",)))

    def test_get_distinct_resource_query_filters(self):
        """Test resource filter method"""
        # Add resources: res1, res2, except1
        self.rule.append("resources", {"filter": "res1", "exception": 0})
        self.rule.append("resources", {"filter": "res2", "exception": 0})
        self.rule.append("resources", {"filter": "except1", "exception": 1})

        result = self.rule.get_distinct_resource_query_filters()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ("Permit", "res1", ("except1",)))
        self.assertEqual(result[1], ("Permit", "res2", ("except1",)))

    def test_get_distinct_query_filters_only_one_non_exception(self):
        """Test with only one non-exception filter"""
        self.rule.append("principals", {"filter": "allow1", "exception": 0})
        self.rule.append("principals", {"filter": "forbid1", "exception": 1})
        self.rule.append("principals", {"filter": "forbid2", "exception": 1})

        result = self.rule.get_distinct_principal_query_filters()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ("Permit", "allow1", ("forbid1", "forbid2")))

    def test_get_distinct_query_filters_empty_list(self):
        """Test with empty filter list"""
        result = self.rule.get_distinct_principal_query_filters()

        # Should return empty list
        self.assertEqual(result, [])

    def test_get_distinct_query_filters_only_exceptions(self):
        """Test with only exception filters (edge case)"""
        self.rule.append("principals", {"filter": "except1", "exception": 1})
        self.rule.append("principals", {"filter": "except2", "exception": 1})

        result = self.rule.get_distinct_principal_query_filters()

        # Should return empty list (no non-exception filters)
        self.assertEqual(result, [])
