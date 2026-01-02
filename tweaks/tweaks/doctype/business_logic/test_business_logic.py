# Copyright (c) 2025, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBusinessLogic(FrappeTestCase):
    """Test cases for Business Logic doctype"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a test Business Logic Category if it doesn't exist
        if not frappe.db.exists("Business Logic Category", "Test Category"):
            category = frappe.get_doc({
                "doctype": "Business Logic Category",
                "category_name": "Test Category",
                "naming_series": "TC"
            })
            category.insert(ignore_permissions=True)

    def tearDown(self):
        """Clean up after tests"""
        # Clean up test Business Logic documents
        frappe.db.delete("Business Logic", {"category": "Test Category"})
        frappe.db.commit()

    def test_business_logic_creation(self):
        """Test creating a Business Logic document"""
        doc = frappe.get_doc({
            "doctype": "Business Logic",
            "title": "Test Business Logic",
            "category": "Test Category",
            "status": "Active"
        })
        doc.insert(ignore_permissions=True)
        
        # Verify document was created
        self.assertTrue(frappe.db.exists("Business Logic", doc.name))
        
        # Verify fields are set correctly
        saved_doc = frappe.get_doc("Business Logic", doc.name)
        self.assertEqual(saved_doc.title, "Test Business Logic")
        self.assertEqual(saved_doc.category, "Test Category")
        self.assertEqual(saved_doc.status, "Active")
        
        # Clean up
        doc.delete()

    def test_business_logic_naming(self):
        """Test Business Logic naming series generation"""
        doc = frappe.get_doc({
            "doctype": "Business Logic",
            "title": "Test Naming",
            "category": "Test Category",
            "status": "Active"
        })
        doc.insert(ignore_permissions=True)
        
        # Verify naming series includes category and year
        self.assertIn("BL", doc.name)
        self.assertIn("TC", doc.name)  # Category naming series
        self.assertIn(str(frappe.utils.getdate().year), doc.name)
        
        # Clean up
        doc.delete()

    def test_business_logic_required_fields(self):
        """Test that required fields are enforced"""
        # Test missing title
        with self.assertRaises(frappe.exceptions.MandatoryError):
            doc = frappe.get_doc({
                "doctype": "Business Logic",
                "category": "Test Category",
                "status": "Active"
            })
            doc.insert(ignore_permissions=True)
        
        # Test missing category
        with self.assertRaises(frappe.exceptions.MandatoryError):
            doc = frappe.get_doc({
                "doctype": "Business Logic",
                "title": "Test No Category",
                "status": "Active"
            })
            doc.insert(ignore_permissions=True)
