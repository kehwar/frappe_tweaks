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
                    "source_document_type": "Customer",
                    "target_document_type": "Contact",
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
            source_document_name="Test Customer",
            context={"test": "context"},
        )

        self.assertTrue(frappe.db.exists("Sync Job", sync_job.name))
        self.assertEqual(sync_job.status, "Queued")
        self.assertEqual(sync_job.source_document_type, "Customer")
        self.assertEqual(sync_job.source_document_name, "Test Customer")

        # Check JSON fields
        context = json.loads(sync_job.context)
        self.assertEqual(context["test"], "context")

    def test_cancel_sync_job(self):
        """Test canceling a sync job"""
        from tweaks.utils.sync_job import enqueue_sync_job

        sync_job = enqueue_sync_job(
            sync_job_type="Test Customer Sync",
            source_document_name="Test Customer",
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

    def test_create_sync_job_without_source_document(self):
        """Test creating a sync job without source document"""
        from tweaks.utils.sync_job import enqueue_sync_job

        # Create sync job without source_document_name
        sync_job = enqueue_sync_job(
            sync_job_type="Test Customer Sync",
            source_document_type="Customer",
            context={"component_names": ["Item1", "Item2"]},
            queue_on_insert=False,  # Don't queue to avoid execution
        )

        self.assertTrue(frappe.db.exists("Sync Job", sync_job.name))
        self.assertEqual(sync_job.status, "Pending")
        self.assertEqual(sync_job.source_document_type, "Customer")
        self.assertIsNone(sync_job.source_document_name)
        
        # Check title generation for context-based sync
        self.assertIn("context-based", sync_job.title)
        
        # Check context
        context = json.loads(sync_job.context)
        self.assertEqual(context["component_names"], ["Item1", "Item2"])

    def test_get_source_document_handles_missing_document(self):
        """Test that get_source_document returns None for deleted documents"""
        from tweaks.utils.sync_job import enqueue_sync_job

        # Create sync job with a non-existent source document
        sync_job = enqueue_sync_job(
            sync_job_type="Test Customer Sync",
            source_document_name="NonExistent Customer",
            context={"test": "data"},
            queue_on_insert=False,  # Don't queue to avoid execution
        )

        # get_source_document should return None for missing document
        source_doc = sync_job.get_source_document()
        self.assertIsNone(source_doc)

    def test_get_source_document_returns_none_when_no_name(self):
        """Test that get_source_document returns None when source_document_name is None"""
        from tweaks.utils.sync_job import enqueue_sync_job

        sync_job = enqueue_sync_job(
            sync_job_type="Test Customer Sync",
            source_document_type="Customer",
            context={"test": "data"},
            queue_on_insert=False,  # Don't queue to avoid execution
        )

        # get_source_document should return None when no name is set
        source_doc = sync_job.get_source_document()
        self.assertIsNone(source_doc)
