# Copyright (c) 2025, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDuckDBUtils(FrappeTestCase):
    """Test cases for duckdb utility functions"""

    def test_load_list_of_dicts(self):
        """Test loading a list of dictionaries"""
        from tweaks.utils.duckdb import load

        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35},
        ]

        duckdata = load(data)

        # Should return a DuckDBData instance
        self.assertIsNotNone(duckdata)
        self.assertTrue(hasattr(duckdata, "query"))

        # Should be able to query the data
        result = duckdata.query("SELECT * FROM data WHERE age > 26")
        rows = result.fetchall()

        # Should return Alice and Charlie
        self.assertEqual(len(rows), 2)

        # Clean up
        duckdata.close()

    def test_query_with_aggregation(self):
        """Test queries with aggregation functions"""
        from tweaks.utils.duckdb import load

        data = [
            {"product": "Apple", "quantity": 10, "price": 1.5},
            {"product": "Banana", "quantity": 5, "price": 0.8},
            {"product": "Orange", "quantity": 8, "price": 1.2},
        ]

        duckdata = load(data)

        # Calculate total value
        result = duckdata.query("SELECT SUM(quantity * price) as total FROM data")
        total = result.fetchone()[0]

        # Should calculate correctly: (10*1.5) + (5*0.8) + (8*1.2) = 15 + 4 + 9.6 = 28.6
        self.assertAlmostEqual(total, 28.6, places=2)

        duckdata.close()

    def test_context_manager(self):
        """Test using DuckDBData as a context manager"""
        from tweaks.utils.duckdb import load

        data = [{"id": 1, "value": "test"}]

        with load(data) as duckdata:
            result = duckdata.query("SELECT COUNT(*) FROM data")
            count = result.fetchone()[0]
            self.assertEqual(count, 1)

    def test_load_with_custom_table_name(self):
        """Test loading data with a custom table name"""
        from tweaks.utils.duckdb import load

        data = [{"x": 1}, {"x": 2}, {"x": 3}]

        duckdata = load(data, table_name="my_table")

        result = duckdata.query("SELECT SUM(x) FROM my_table")
        total = result.fetchone()[0]

        self.assertEqual(total, 6)

        duckdata.close()

    def test_load_none_data(self):
        """Test that loading None data throws an error"""
        from tweaks.utils.duckdb import load

        with self.assertRaises(frappe.ValidationError):
            load(None)

    def test_query_with_filtering(self):
        """Test complex queries with filtering and ordering"""
        from tweaks.utils.duckdb import load

        data = [
            {"name": "Alice", "score": 85},
            {"name": "Bob", "score": 92},
            {"name": "Charlie", "score": 78},
            {"name": "David", "score": 95},
        ]

        duckdata = load(data)

        result = duckdata.query(
            "SELECT name, score FROM data WHERE score >= 85 ORDER BY score DESC"
        )
        rows = result.fetchall()

        # Should return David, Bob, Alice in that order
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0], "David")
        self.assertEqual(rows[1][0], "Bob")
        self.assertEqual(rows[2][0], "Alice")

        duckdata.close()
