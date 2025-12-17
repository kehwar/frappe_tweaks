# Copyright (c) 2025, and contributors
# For license information, please see license.txt

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSyncJob(FrappeTestCase):
    """Test Sync Job functionality"""

    def setUp(self):
        """Create test Sync Job Type"""
        # Create test Sync Job Type if not exists
        if not frappe.db.exists("Sync Job Type", "Test Customer Sync"):
            sync_job_type = frappe.get_doc(
                {
                    "doctype": "Sync Job Type",
                    "sync_job_type_name": "Test Customer Sync",
                    "module": "Soldamundo",
                    "source_doctype": "Customer",
                    "target_doctype": "Contact",
                    "is_standard": "No",
                    "queue": "default",
                    "timeout": 300,
                    "retry_delay": 5,
                    "max_retries": 3,
                }
            )
            sync_job_type.insert(ignore_permissions=True)

        # Create test Customer
        if not frappe.db.exists("Customer", "Test Customer"):
            customer = frappe.get_doc(
                {
                    "doctype": "Customer",
                    "customer_name": "Test Customer",
                    "customer_type": "Individual",
                    "customer_group": "Individual",
                    "territory": "All Territories",
                }
            )
            customer.insert(ignore_permissions=True)

    def tearDown(self):
        """Clean up test data"""
        # Delete test Sync Jobs
        frappe.db.delete("Sync Job", {"sync_job_type": "Test Customer Sync"})

        # Delete test Customer
        if frappe.db.exists("Customer", "Test Customer"):
            frappe.delete_doc("Customer", "Test Customer", ignore_permissions=True)

        # Delete test Sync Job Type
        if frappe.db.exists("Sync Job Type", "Test Customer Sync"):
            frappe.delete_doc(
                "Sync Job Type", "Test Customer Sync", ignore_permissions=True
            )

    def test_create_sync_job(self):
        """Test creating a sync job"""
        from tweaks.utils.sync_job import enqueue_sync_job

        sync_job = enqueue_sync_job(
            sync_job_type="Test Customer Sync",
            source_doc_name="Test Customer",
            context={"test": "context"},
        )

        self.assertTrue(frappe.db.exists("Sync Job", sync_job.name))
        self.assertEqual(sync_job.status, "Queued")
        self.assertEqual(sync_job.source_doctype, "Customer")
        self.assertEqual(sync_job.source_document_name, "Test Customer")

        # Check JSON fields
        context = json.loads(sync_job.context)
        self.assertEqual(context["test"], "context")

    def test_cancel_sync_job(self):
        """Test canceling a sync job"""
        from tweaks.utils.sync_job import enqueue_sync_job

        sync_job = enqueue_sync_job(
            sync_job_type="Test Customer Sync",
            source_doc_name="Test Customer",
        )

        # Cancel job
        sync_job.cancel_sync(reason="Test cancellation")

        sync_job.reload()
        self.assertEqual(sync_job.status, "Canceled")
        self.assertEqual(sync_job.cancel_reason, "Test cancellation")

    def test_validate_context_json(self):
        """Test context JSON validation"""
        from tweaks.utils.sync_job import enqueue_sync_job

        # Invalid JSON should raise error
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Sync Job",
                    "sync_job_type": "Test Customer Sync",
                    "source_doctype": "Customer",
                    "source_document_name": "Test Customer",
                    "context": "invalid json",
                }
            ).insert(ignore_permissions=True)

    def test_get_sync_job_module_path(self):
        """Test sync job module path generation"""
        from tweaks.utils.sync_job import get_sync_job_module_dotted_path

        path = get_sync_job_module_dotted_path("Soldamundo", "SAP Customer Sync")
        self.assertEqual(
            path, "soldamundo.soldamundo.sync_job.sap_customer_sync.sap_customer_sync"
        )
