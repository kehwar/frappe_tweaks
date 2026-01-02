# Copyright (c) 2025, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from tweaks.utils.changelog import frappe_version


class TestChangelogUtils(FrappeTestCase):
    """Test cases for changelog utility functions"""

    def test_frappe_version(self):
        """Test frappe_version function returns an integer"""
        version = frappe_version()
        
        # Should return an integer
        self.assertIsInstance(version, int)
        
        # Should be a reasonable version number (between 10 and 20 for current Frappe versions)
        self.assertGreaterEqual(version, 10)
        self.assertLessEqual(version, 20)
        
    def test_frappe_version_matches_actual_version(self):
        """Test that the extracted version matches the actual Frappe version"""
        version = frappe_version()
        actual_major_version = int(frappe.__version__.split(".")[0])
        
        self.assertEqual(version, actual_major_version)
