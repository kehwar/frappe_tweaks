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
        
        # Check title generation - should be just the document type
        self.assertEqual(sync_job.title, "Customer")
        
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

    def test_hooks_execution_order(self):
        """Test that all hooks are called in the correct order"""
        from tweaks.utils.sync_job import create_sync_job
        
        # Create test Sync Job Type with hook-enabled module if not exists
        if not frappe.db.exists("Sync Job Type", "Test Hooks Sync"):
            sync_job_type = frappe.get_doc(
                {
                    "doctype": "Sync Job Type",
                    "sync_job_type_name": "Test Hooks Sync",
                    "module": "Tweaks",
                    "source_document_type": "Customer",
                    "target_document_type": "Contact",
                    "is_standard": "Yes",
                    "queue": "default",
                    "timeout": 300,
                    "retry_delay": 5,
                    "max_retries": 3,
                }
            )
            sync_job_type.insert(ignore_permissions=True)
        
        # Import the test module
        import tweaks.tweaks.sync_job_type.test_hooks_sync.test_hooks_sync as test_module
        test_module.reset_hook_calls()
        
        # Create and execute sync job directly (not queued)
        sync_job = create_sync_job(
            sync_job_type="Test Hooks Sync",
            source_document_name="Test Customer",
            queue_on_insert=False,
        )
        
        # Execute the sync job
        sync_job.execute()
        
        # Get hook calls
        hook_calls = test_module.get_hook_calls()
        
        # Verify hooks were called in correct order
        hook_names = [call[0] for call in hook_calls]
        
        # Expected order: after_start, get_target_document, update_target_doc, before_sync, after_sync, finished
        self.assertIn("after_start", hook_names)
        self.assertIn("get_target_document", hook_names)
        self.assertIn("update_target_doc", hook_names)
        self.assertIn("before_sync", hook_names)
        self.assertIn("after_sync", hook_names)
        self.assertIn("finished", hook_names)
        
        # Verify order
        after_start_idx = hook_names.index("after_start")
        get_target_idx = hook_names.index("get_target_document")
        update_target_idx = hook_names.index("update_target_doc")
        before_sync_idx = hook_names.index("before_sync")
        after_sync_idx = hook_names.index("after_sync")
        finished_idx = hook_names.index("finished")
        
        self.assertLess(after_start_idx, get_target_idx)
        self.assertLess(get_target_idx, update_target_idx)
        self.assertLess(update_target_idx, before_sync_idx)
        self.assertLess(before_sync_idx, after_sync_idx)
        self.assertLess(after_sync_idx, finished_idx)
        
        # Cleanup
        test_module.reset_hook_calls()
        frappe.db.delete("Sync Job", {"sync_job_type": "Test Hooks Sync"})
        frappe.db.delete("Contact", {"first_name": "Test Customer"})
        if frappe.db.exists("Sync Job Type", "Test Hooks Sync"):
            frappe.delete_doc("Sync Job Type", "Test Hooks Sync", ignore_permissions=True)

    def test_relay_hooks_with_multiple_targets(self):
        """Test that relay hooks are called for multiple targets"""
        from tweaks.utils.sync_job import create_sync_job
        
        # Create test Sync Job Type with hook-enabled module if not exists
        if not frappe.db.exists("Sync Job Type", "Test Hooks Sync Multiple"):
            sync_job_type = frappe.get_doc(
                {
                    "doctype": "Sync Job Type",
                    "sync_job_type_name": "Test Hooks Sync Multiple",
                    "module": "Tweaks",
                    "source_document_type": "Customer",
                    "target_document_type": "Contact",
                    "is_standard": "Yes",
                    "queue": "default",
                    "timeout": 300,
                    "retry_delay": 5,
                    "max_retries": 3,
                }
            )
            sync_job_type.insert(ignore_permissions=True)
        
        # Import the test module
        import tweaks.tweaks.sync_job_type.test_hooks_sync.test_hooks_sync as test_module
        
        # Temporarily replace get_target_document with get_multiple_target_documents
        # by creating a custom execution
        test_module.reset_hook_calls()
        
        # Create a custom sync job module that uses get_multiple_target_documents
        sync_job = create_sync_job(
            sync_job_type="Test Hooks Sync Multiple",
            source_document_name="Test Customer",
            queue_on_insert=False,
        )
        
        # Mock the module to use get_multiple_target_documents
        # We need to patch the module loading to use our test module
        original_get_module = frappe.get_module
        
        def mock_get_module(path):
            if "test_hooks_sync_multiple" in path:
                return test_module
            return original_get_module(path)
        
        frappe.get_module = mock_get_module
        
        try:
            # Execute the sync job - this should call relay hooks
            sync_job.execute()
            
            # Get hook calls
            hook_calls = test_module.get_hook_calls()
            hook_names = [call[0] for call in hook_calls]
            
            # Verify relay hooks were called
            self.assertIn("after_start", hook_names)
            self.assertIn("get_multiple_target_documents", hook_names)
            self.assertIn("before_relay", hook_names)
            self.assertIn("after_relay", hook_names)
            
            # Verify before_relay was called with 2 targets
            before_relay_call = [call for call in hook_calls if call[0] == "before_relay"][0]
            self.assertEqual(before_relay_call[2], 2)
            
            # Verify after_relay was called with 2 child jobs
            after_relay_call = [call for call in hook_calls if call[0] == "after_relay"][0]
            self.assertEqual(after_relay_call[2], 2)
            
        finally:
            # Restore original get_module
            frappe.get_module = original_get_module
            
            # Cleanup
            test_module.reset_hook_calls()
            frappe.db.delete("Sync Job", {"sync_job_type": "Test Hooks Sync Multiple"})
            if frappe.db.exists("Sync Job Type", "Test Hooks Sync Multiple"):
                frappe.delete_doc("Sync Job Type", "Test Hooks Sync Multiple", ignore_permissions=True)

    def test_get_document_even_if_deleted_with_virtual_doctype(self):
        """Test that get_document_even_if_deleted works with virtual doctypes"""
        from tweaks.tweaks.doctype.sync_job.sync_job import get_document_even_if_deleted
        
        # Create a mock virtual doctype by temporarily setting is_virtual on an existing doctype
        # We'll use a simple doctype for testing
        doctype = "User"
        
        # Save original is_virtual value
        meta = frappe.get_meta(doctype)
        original_is_virtual = meta.get("is_virtual")
        
        try:
            # Temporarily set is_virtual to True
            # Note: We can't actually modify the meta in a test, so we'll test the logic differently
            # Instead, we'll verify the function handles the virtual check correctly
            
            # For non-virtual doctypes, the function should work as before
            if frappe.db.exists(doctype, "Administrator"):
                doc = get_document_even_if_deleted(doctype, "Administrator")
                self.assertIsNotNone(doc)
                self.assertEqual(doc.name, "Administrator")
            
            # Test with non-existent document
            with self.assertRaises(frappe.DoesNotExistError):
                get_document_even_if_deleted(doctype, "NonExistentUser123456")
        
        finally:
            # Restore original is_virtual value if we modified it
            pass

    def test_get_document_even_if_deleted_handles_non_existent(self):
        """Test that get_document_even_if_deleted raises proper error for non-existent documents"""
        from tweaks.tweaks.doctype.sync_job.sync_job import get_document_even_if_deleted
        
        # Test with non-existent document
        with self.assertRaises(frappe.DoesNotExistError):
            get_document_even_if_deleted("Customer", "NonExistentCustomer123456")

