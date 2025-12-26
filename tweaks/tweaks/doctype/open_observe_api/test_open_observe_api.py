# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOpenObserveAPI(FrappeTestCase):
    """
    Test cases for OpenObserve API integration.
    """

    def setUp(self):
        """Set up test fixtures."""
        # Create or update test configuration
        if not frappe.db.exists("Open Observe API", "Open Observe API"):
            doc = frappe.get_doc({
                "doctype": "Open Observe API",
                "url": "https://test.openobserve.ai",
                "user": "test@example.com",
                "password": "test_password",
                "default_org": "default"
            })
            doc.insert()
        else:
            doc = frappe.get_doc("Open Observe API", "Open Observe API")
            doc.url = "https://test.openobserve.ai"
            doc.user = "test@example.com"
            doc.password = "test_password"
            doc.default_org = "default"
            doc.save()

    def test_validate_setup(self):
        """Test configuration validation."""
        doc = frappe.get_doc("Open Observe API", "Open Observe API")
        
        # Should not raise an error with valid config
        doc.validate_setup()
        
        # Test missing URL
        doc.url = ""
        with self.assertRaises(frappe.ValidationError):
            doc.validate_setup()

    def test_get_auth_header(self):
        """Test authentication header generation."""
        doc = frappe.get_doc("Open Observe API", "Open Observe API")
        headers = doc.get_auth_header()
        
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Basic "))

    def tearDown(self):
        """Clean up test data."""
        frappe.db.rollback()
