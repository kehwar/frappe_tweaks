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

    def test_assign_condition(self):
        """Test that assign_condition controls when users are assigned"""
        # Create a rule with assign_condition that checks a field value
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Assign Condition",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Review needed"}',
                "mandatory": 0,
                "assign_condition": "result = doc.priority == 'High'",
                "users": [
                    {"user": self.test_user_1, "ignore_permissions": 1},
                ],
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document with Low priority (should NOT assign)
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for assign condition",
                "priority": "Low",
            }
        )
        test_doc.insert(ignore_permissions=True)

        # Trigger document review evaluation
        from tweaks.utils.document_review import evaluate_document_reviews

        evaluate_document_reviews(test_doc)

        # Check that user was NOT assigned
        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": test_doc.doctype,
                "reference_name": test_doc.name,
                "status": "Open",
            },
        )
        self.assertEqual(len(assignments), 0, "User should NOT be assigned when condition is false")

        # Update document to High priority (should assign)
        test_doc.priority = "High"
        test_doc.save(ignore_permissions=True)
        evaluate_document_reviews(test_doc)

        # Check that user was assigned
        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": test_doc.doctype,
                "reference_name": test_doc.name,
                "status": "Open",
            },
            fields=["allocated_to"],
        )
        self.assertTrue(len(assignments) > 0, "User should be assigned when condition is true")
        self.assertEqual(assignments[0].allocated_to, self.test_user_1)

        # Clean up
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
            },
        )
        for r in review:
            frappe.delete_doc("Document Review", r.name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_unassign_condition(self):
        """Test that unassign_condition clears all assignments"""
        # Create a rule with both assign and unassign conditions
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Unassign Condition",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Review needed"}',
                "mandatory": 0,
                "assign_condition": "result = doc.priority == 'High'",
                "unassign_condition": "result = doc.status == 'Closed'",
                "users": [
                    {"user": self.test_user_1, "ignore_permissions": 1},
                ],
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document with High priority (should assign)
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for unassign condition",
                "priority": "High",
                "status": "Open",
            }
        )
        test_doc.insert(ignore_permissions=True)
        
        from tweaks.utils.document_review import evaluate_document_reviews
        evaluate_document_reviews(test_doc)

        # Check that user was assigned
        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": test_doc.doctype,
                "reference_name": test_doc.name,
                "status": "Open",
            },
        )
        self.assertTrue(len(assignments) > 0, "User should be assigned")

        # Close the document (should unassign)
        test_doc.status = "Closed"
        test_doc.save(ignore_permissions=True)
        evaluate_document_reviews(test_doc)

        # Check that assignments were cleared
        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": test_doc.doctype,
                "reference_name": test_doc.name,
                "status": ("not in", ("Cancelled", "Closed")),
            },
        )
        self.assertEqual(len(assignments), 0, "Assignments should be cleared when unassign condition is true")

        # Clean up
        review = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
            },
        )
        for r in review:
            frappe.delete_doc("Document Review", r.name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_submit_condition_with_docstatus(self):
        """Test that submit_condition auto-submits reviews when condition is met"""
        # Create a submittable test doctype scenario
        # Note: We'll use ToDo for simplicity, but in real usage this would be a submittable doctype
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Submit Condition",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Review needed"}',
                "mandatory": 0,
                "submit_condition": "result = doc.status == 'Closed'",
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for submit condition",
                "status": "Open",
            }
        )
        test_doc.insert(ignore_permissions=True)
        
        from tweaks.utils.document_review import evaluate_document_reviews
        evaluate_document_reviews(test_doc)

        # Check that review was created
        reviews = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "docstatus": 0,
            },
        )
        self.assertTrue(len(reviews) > 0, "Draft review should be created")

        # Close the document (should trigger submit condition)
        test_doc.status = "Closed"
        test_doc.save(ignore_permissions=True)
        evaluate_document_reviews(test_doc)

        # Check that review was submitted
        submitted_reviews = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "docstatus": 1,
            },
        )
        self.assertTrue(len(submitted_reviews) > 0, "Review should be auto-submitted when condition is true")

        # Clean up
        for r in frappe.get_all("Document Review", filters={"reference_doctype": test_doc.doctype, "reference_name": test_doc.name}):
            frappe.delete_doc("Document Review", r.name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_validate_condition_blocks_when_reviews_pending(self):
        """Test that validate_condition throws error when draft reviews exist"""
        # Create a rule with validate condition
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test Validate Condition",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Review needed"}',
                "mandatory": 1,
                "validate_condition": "result = doc.status == 'Closed'",
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for validate condition",
                "status": "Open",
            }
        )
        test_doc.insert(ignore_permissions=True)
        
        from tweaks.utils.document_review import evaluate_document_reviews
        evaluate_document_reviews(test_doc)

        # Check that review was created
        reviews = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
                "docstatus": 0,
            },
        )
        self.assertTrue(len(reviews) > 0, "Draft review should be created")

        # Try to close the document (should trigger validation and throw error)
        test_doc.status = "Closed"
        test_doc.save(ignore_permissions=True)
        
        with self.assertRaises(frappe.ValidationError):
            evaluate_document_reviews(test_doc)

        # Clean up
        for r in frappe.get_all("Document Review", filters={"reference_doctype": test_doc.doctype, "reference_name": test_doc.name}):
            frappe.delete_doc("Document Review", r.name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)

    def test_conditions_with_no_script_means_no_action(self):
        """Test that empty condition scripts don't trigger actions"""
        # Create a rule without any conditions
        rule = frappe.get_doc(
            {
                "doctype": "Document Review Rule",
                "title": "Test No Conditions",
                "reference_doctype": "ToDo",
                "script": 'result = {"message": "Review needed"}',
                "mandatory": 0,
                "users": [
                    {"user": self.test_user_1, "ignore_permissions": 1},
                ],
            }
        )
        rule.insert(ignore_permissions=True)

        # Create a test document
        test_doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Test document for no conditions",
            }
        )
        test_doc.insert(ignore_permissions=True)
        
        from tweaks.utils.document_review import evaluate_document_reviews
        evaluate_document_reviews(test_doc)

        # Check that review was created but user was NOT assigned (no assign_condition)
        reviews = frappe.get_all(
            "Document Review",
            filters={
                "reference_doctype": test_doc.doctype,
                "reference_name": test_doc.name,
            },
        )
        self.assertTrue(len(reviews) > 0, "Review should be created")

        assignments = frappe.get_all(
            "ToDo",
            filters={
                "reference_type": test_doc.doctype,
                "reference_name": test_doc.name,
                "status": "Open",
            },
        )
        self.assertEqual(len(assignments), 0, "User should NOT be assigned without assign_condition")

        # Clean up
        for r in reviews:
            frappe.delete_doc("Document Review", r.name, force=1)
        frappe.delete_doc("ToDo", test_doc.name, force=1)
        frappe.delete_doc("Document Review Rule", rule.name, force=1)


