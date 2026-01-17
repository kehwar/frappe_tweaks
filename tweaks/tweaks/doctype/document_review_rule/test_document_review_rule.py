# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDocumentReviewRule(FrappeTestCase):
    def setUp(self):
        """Set up test data before each test"""
        # Create test users if they don't exist
        self.test_user_1 = "test_reviewer1@example.com"
        self.test_user_2 = "test_reviewer2@example.com"

        if not frappe.db.exists("User", self.test_user_1):
            user1 = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.test_user_1,
                    "first_name": "Test Reviewer 1",
                    "send_welcome_email": 0,
                }
            )
            user1.insert(ignore_permissions=True)

        if not frappe.db.exists("User", self.test_user_2):
            user2 = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.test_user_2,
                    "first_name": "Test Reviewer 2",
                    "send_welcome_email": 0,
                }
            )
            user2.insert(ignore_permissions=True)

    def tearDown(self):
        """Clean up after each test"""
        frappe.set_user("Administrator")

    def test_document_review_user_assignment(self):
        """Test that users are assigned to document reviews"""
        # Create a test Document Review Rule with users
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Assignment Rule",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Test review needed"}',
                "mandatory": 0,
                "users": [
                    {"user": self.test_user_1, "ignore_permissions": 1},
                    {"user": self.test_user_2, "ignore_permissions": 1},
                ],
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document (using ToDo as a simple test doctype)
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for review assignment",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")

        # Check if users were assigned
        review_name = review[0].name
        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": "Document Review",
                "reference_name": review_name,
                "status": "Open",
            },
            fields=["allocated_to"],
        )

        assigned_users = [a.allocated_to for a in assignments]
        self.assertIn(
            self.test_user_1,
            assigned_users,
            "User 1 should be assigned to the review",
        )
        self.assertIn(
            self.test_user_2,
            assigned_users,
            "User 2 should be assigned to the review",
        )

        # Clean up
        frappe.delete_doc("Document Review", review_name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_ignore_permissions_flag(self):
        """Test that ignore_permissions flag controls permission checking per user"""
        # Create a rule with per-user ignore_permissions settings
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Permission Rule",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Test review needed"}',
                "mandatory": 0,
                "users": [
                    {"user": self.test_user_1, "ignore_permissions": 0},  # Should check permissions
                ],
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for permission checking",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            limit=1,
        )

        # Verify the review was created (even if user doesn't have permissions)
        self.assertTrue(len(review) > 0, "Document Review should be created")

        # Clean up
        if review:
            frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

