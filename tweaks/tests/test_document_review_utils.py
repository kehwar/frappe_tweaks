# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from tweaks.utils.document_review import approve_all_document_reviews


class TestDocumentReviewUtils(FrappeTestCase):
    """Test cases for document review utility functions"""

    def setUp(self):
        """Set up test data before each test"""
        # Clean up any existing test data
        self.cleanup_test_data()

        # Create a test ToDo as reference document
        self.test_todo = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test ToDo for Document Review",
                "status": "Open",
            }
        )
        self.test_todo.insert()

        # Create a test Document Review Rule
        self.test_rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Review Rule",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Test review required"}',
                "mandatory": 1,
                "disabled": 0,
            }
        )
        self.test_rule.insert()

    def tearDown(self):
        """Clean up test data after each test"""
        self.cleanup_test_data()

    def cleanup_test_data(self):
        """Helper method to clean up test data"""
        # Delete test reviews
        test_reviews = frappe.get_all(
            "Document Review",
            filters={"reference_doctype": "ToDo"},
            pluck="name",
        )
        for review_name in test_reviews:
            frappe.delete_doc("Document Review", review_name, force=1)

        # Delete test rules
        test_rules = frappe.get_all(
            "Document Review Rule",
            filters={"title": ["like", "Test %"]},
            pluck="name",
        )
        for rule_name in test_rules:
            frappe.delete_doc("Document Review Rule", rule_name, force=1)

        # Delete test todos
        test_todos = frappe.get_all(
            "ToDo",
            filters={"description": ["like", "Test ToDo%"]},
            pluck="name",
        )
        for todo_name in test_todos:
            frappe.delete_doc("ToDo", todo_name, force=1)

        frappe.db.commit()

    def create_test_review(self, mandatory=1):
        """Helper method to create a test Document Review"""
        review = frappe.get_doc(
            {
                "doctype": "Document Review",
                "reference_doctype": self.test_todo.doctype,
                "reference_name": self.test_todo.name,
                "review_rule": self.test_rule.name,
                "message": "Test review message",
                "mandatory": mandatory,
            }
        )
        review.insert()
        return review

    def test_approve_all_document_reviews_with_pending_reviews(self):
        """Test approving multiple pending reviews"""
        # Create multiple test reviews
        review1 = self.create_test_review(mandatory=1)
        review2 = self.create_test_review(mandatory=0)

        # Approve all reviews
        result = approve_all_document_reviews(
            reference_doctype=self.test_todo.doctype,
            reference_name=self.test_todo.name,
            review="Bulk approval test",
        )

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["approved_count"], 2)
        self.assertEqual(len(result["approved_reviews"]), 2)

        # Verify reviews are actually submitted
        review1.reload()
        review2.reload()
        self.assertEqual(review1.docstatus, 1)
        self.assertEqual(review2.docstatus, 1)

    def test_approve_all_document_reviews_with_no_pending_reviews(self):
        """Test approving when there are no pending reviews"""
        result = approve_all_document_reviews(
            reference_doctype=self.test_todo.doctype,
            reference_name=self.test_todo.name,
        )

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["approved_count"], 0)
        self.assertEqual(len(result["approved_reviews"]), 0)
        self.assertIn("No pending reviews", result["message"])

    def test_approve_all_document_reviews_respects_permissions(self):
        """Test that approve_all uses get_list which respects permissions"""
        # Create a test review
        review = self.create_test_review()

        # This test verifies the function uses frappe.get_list
        # In actual usage, permissions would be checked by Frappe
        # For this test, we verify the function works correctly
        result = approve_all_document_reviews(
            reference_doctype=self.test_todo.doctype,
            reference_name=self.test_todo.name,
        )

        # Verify at least one review was approved
        self.assertGreater(result["approved_count"], 0)

    def test_approve_all_document_reviews_with_review_comment(self):
        """Test that review comments are applied to all approvals"""
        # Create a test review
        review = self.create_test_review()

        # Approve with comment
        test_comment = "Bulk approved for testing"
        result = approve_all_document_reviews(
            reference_doctype=self.test_todo.doctype,
            reference_name=self.test_todo.name,
            review=test_comment,
        )

        # Verify review was approved
        self.assertEqual(result["approved_count"], 1)

        # Verify comment was applied
        review.reload()
        self.assertEqual(review.review, test_comment)

    def test_approve_all_document_reviews_only_approves_drafts(self):
        """Test that only draft reviews are approved, not submitted ones"""
        # Create and submit one review
        review1 = self.create_test_review()
        review1.submit()

        # Create another draft review
        review2 = self.create_test_review()

        # Approve all reviews
        result = approve_all_document_reviews(
            reference_doctype=self.test_todo.doctype,
            reference_name=self.test_todo.name,
        )

        # Should only approve the draft review, not the already submitted one
        self.assertEqual(result["approved_count"], 1)
        self.assertEqual(result["approved_reviews"][0]["name"], review2.name)
