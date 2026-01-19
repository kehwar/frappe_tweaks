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

    def test_direct_message_variable(self):
        """Test that message variable can be set directly without result dict"""
        # Create a test Document Review Rule using direct message variable
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Direct Message Variable",
                "reference_doctype": "ToDo",
                "script": 'message = "Direct message test"',
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for direct message variable",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created with the message
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            fields=["name", "message"],
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")
        self.assertEqual(
            review[0].message,
            "Direct message test",
            "Message should be set from message variable",
        )

        # Clean up
        frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_direct_message_and_data_variables(self):
        """Test that message and data variables can be set directly together"""
        # Create a test Document Review Rule using direct message and data variables
        script_content = """message = "Direct message with data"
data = {"key1": "value1", "key2": 123}"""
        
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Direct Message and Data Variables",
                "reference_doctype": "ToDo",
                "script": script_content,
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for direct message and data variables",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created with message and data
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            fields=["name", "message", "review_data"],
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")
        self.assertEqual(
            review[0].message,
            "Direct message with data",
            "Message should be set from message variable",
        )

        # Get the full review document to check review_data
        review_doc = frappe.get_doc("Document Review", review[0].name)
        self.assertIsNotNone(review_doc.review_data, "Review data should be set")
        self.assertEqual(
            review_doc.review_data.get("key1"),
            "value1",
            "Data should contain key1",
        )
        self.assertEqual(
            review_doc.review_data.get("key2"), 123, "Data should contain key2"
        )

        # Clean up
        frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_result_variable_still_works(self):
        """Test that the traditional result variable approach still works"""
        # Create a test Document Review Rule using traditional result variable
        script_content = """result = {
    "message": "Traditional result message",
    "data": {"old": "style"}
}"""
        
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Result Variable Backward Compatibility",
                "reference_doctype": "ToDo",
                "script": script_content,
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for result variable backward compatibility",
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
            fields=["name", "message"],
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")
        self.assertEqual(
            review[0].message,
            "Traditional result message",
            "Message should be set from result variable",
        )

        # Clean up
        frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_result_takes_precedence_over_direct_variables(self):
        """Test that result variable takes precedence over direct message/data variables"""
        # Create a test Document Review Rule that sets both result and direct variables
        script_content = """message = "This should be ignored"
data = {"ignored": "data"}
result = {
    "message": "Result takes precedence",
    "data": {"priority": "high"}
}"""
        
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Result Precedence",
                "reference_doctype": "ToDo",
                "script": script_content,
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for result precedence",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created with result values
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            fields=["name", "message"],
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")
        self.assertEqual(
            review[0].message,
            "Result takes precedence",
            "Message should be from result variable, not direct message",
        )

        # Clean up
        frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_no_review_when_message_not_set(self):
        """Test that no review is created when neither result nor message is set"""
        # Create a test Document Review Rule that doesn't set any variables
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test No Review Creation",
                "reference_doctype": "ToDo",
                "script": 'data = {"some": "data"}  # Only data, no message',
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for no review creation",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check that no Document Review was created
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            limit=1,
        )

        self.assertEqual(
            len(review),
            0,
            "No Document Review should be created when message is not set",
        )

        # Clean up
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_message_template_rendering(self):
        """Test that message_template is rendered with data variable"""
        # Create a test Document Review Rule with message_template
        script_content = """message = "This should be overridden by template"
data = {"item_code": "ITEM-001", "rate": 100, "min_price": 150}"""
        
        message_template = "Item {{ data.item_code }} has rate {{ data.rate }}, which is below minimum price of {{ data.min_price }}."
        
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Message Template",
                "reference_doctype": "ToDo",
                "script": script_content,
                "message_template": message_template,
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for message template",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created with rendered template
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            fields=["name", "message"],
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")
        self.assertEqual(
            review[0].message,
            "Item ITEM-001 has rate 100, which is below minimum price of 150.",
            "Message should be rendered from template with data",
        )

        # Clean up
        frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_message_template_without_data(self):
        """Test that message_template without data falls back to original message"""
        # Create a test Document Review Rule with message_template but no data
        script_content = 'message = "Fallback message"'
        message_template = "This template needs data: {{ data.value }}"
        
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Template Without Data",
                "reference_doctype": "ToDo",
                "script": script_content,
                "message_template": message_template,
                "mandatory": 0,
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for template without data",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check if a Document Review was created with fallback message
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "review_rule": rule.name,
            },
            fields=["name", "message"],
            limit=1,
        )

        self.assertTrue(len(review) > 0, "Document Review should be created")
        self.assertEqual(
            review[0].message,
            "Fallback message",
            "Message should fall back to original message when template has no data",
        )

        # Clean up
        frappe.delete_doc("Document Review", review[0].name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

