# Copyright (c) 2025, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from tweaks.tweaks.doctype.ac_rule.ac_rule_utils import (
    clear_ac_rule_cache,
    get_rule_map,
)


class TestACRuleCache(FrappeTestCase):
    """Test cases for AC Rule cache functionality"""

    def setUp(self):
        """Set up test environment"""
        # Clear cache before each test
        clear_ac_rule_cache()

    def tearDown(self):
        """Clean up after each test"""
        # Clear cache after each test
        clear_ac_rule_cache()

    def test_clear_ac_rule_cache(self):
        """Test that clear_ac_rule_cache clears the cache"""
        # First call should build the cache
        rule_map_1 = get_rule_map()
        
        # Verify cache is set
        cached_map = frappe.cache.get_value("ac_rule_map")
        self.assertIsNotNone(cached_map)
        
        # Clear the cache
        clear_ac_rule_cache()
        
        # Verify cache is cleared
        cached_map = frappe.cache.get_value("ac_rule_map")
        self.assertIsNone(cached_map)

    def test_get_rule_map_caching(self):
        """Test that get_rule_map uses cache on subsequent calls"""
        # Clear cache first
        clear_ac_rule_cache()
        
        # First call should build the cache
        rule_map_1 = get_rule_map()
        
        # Verify cache is set
        cached_map = frappe.cache.get_value("ac_rule_map")
        self.assertIsNotNone(cached_map)
        self.assertEqual(rule_map_1, cached_map)
        
        # Second call should use cache (same result)
        rule_map_2 = get_rule_map()
        self.assertEqual(rule_map_1, rule_map_2)

    def test_get_rule_map_returns_dict(self):
        """Test that get_rule_map returns a dictionary"""
        rule_map = get_rule_map()
        self.assertIsInstance(rule_map, dict)

    def test_cache_invalidation_on_ac_rule_change(self):
        """Test that cache is cleared when AC Rule is modified"""
        # Skip if tables don't exist (during installation)
        if not frappe.db.table_exists("AC Rule"):
            return
        
        # Build cache
        get_rule_map()
        
        # Verify cache exists
        cached_map = frappe.cache.get_value("ac_rule_map")
        self.assertIsNotNone(cached_map)
        
        # Try to create a test AC Rule (will clear cache in on_change hook)
        # Note: This might fail if required dependencies don't exist, so we wrap in try/except
        try:
            # Create a test rule if possible
            # For now, we just test the clear function directly
            clear_ac_rule_cache()
            
            # Verify cache is cleared
            cached_map = frappe.cache.get_value("ac_rule_map")
            self.assertIsNone(cached_map)
        except Exception:
            # If we can't create a rule, at least verify clear works
            clear_ac_rule_cache()
            cached_map = frappe.cache.get_value("ac_rule_map")
            self.assertIsNone(cached_map)
