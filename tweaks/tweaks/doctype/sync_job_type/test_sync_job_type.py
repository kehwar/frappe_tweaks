# Copyright (c) 2025, and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


class UnitTestSyncJobType(UnitTestCase):
    """
    Unit tests for SyncJobType.
    Use this class for testing individual functions and methods.
    """

    pass


class IntegrationTestSyncJobType(IntegrationTestCase):
    """
    Integration tests for SyncJobType.
    Use this class for testing interactions between multiple components.
    """

    def test_create_sync_job_type(self):
        """Test creating a sync job type"""
        sync_job_type = frappe.get_doc(
            {
                "doctype": "Sync Job Type",
                "sync_job_type_name": "Test Sync Type",
                "module": "Tweaks",
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

        self.assertTrue(frappe.db.exists("Sync Job Type", "Test Sync Type"))

        # Clean up
        frappe.delete_doc("Sync Job Type", "Test Sync Type", ignore_permissions=True)

    def test_validate_standard_in_dev_mode(self):
        """Test validation for is_standard in developer mode"""
        # This test requires developer_mode to be enabled
        if not frappe.conf.developer_mode:
            return

        sync_job_type = frappe.get_doc(
            {
                "doctype": "Sync Job Type",
                "sync_job_type_name": "Test Standard Sync",
                "module": "Tweaks",
                "source_document_type": "Customer",
                "target_document_type": "Contact",
                "is_standard": "Yes",
            }
        )

        # Should save without error in dev mode
        sync_job_type.insert(ignore_permissions=True)

        # Clean up
        frappe.delete_doc(
            "Sync Job Type", "Test Standard Sync", ignore_permissions=True
        )
