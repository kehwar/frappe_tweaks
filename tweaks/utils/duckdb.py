"""
DuckDB utilities for safe execution contexts.

This module provides helpers to work with DuckDB in-memory databases
within Frappe's safe execution environment.

The DuckDBQueryable class allows you to:
- Load multiple tables from Python dicts/lists
- Execute SQL queries with parameterization
- Apply transformations (pluck, pick, omit, first)
- Return results as tuples, dicts, or DataFrames
- Use context managers for automatic cleanup
"""

import duckdb
import pandas as pd


class DuckDBQueryable:
    """
    Helper class to work with DuckDB using pandas DataFrames.

    Supports multiple tables, parameterized queries, and flexible result formatting.
    Can be used as a context manager for automatic connection cleanup.

    Usage:
        tables = {
            "people": [
                {"name": "John", "age": 30, "city": "New York"},
                {"name": "Jane", "age": 25, "city": "Boston"},
            ],
            "cities": [
                {"name": "New York", "population": 8000000},
                {"name": "Boston", "population": 700000},
            ]
        }

        # Basic usage
        db = DuckDBQueryable(tables)
        results = db.execute("SELECT * FROM people WHERE age > ?", [28])
        db.close()

        # Context manager (recommended)
        with DuckDBQueryable(tables) as db:
            results = db.execute("SELECT * FROM people WHERE age > ?", [28])
    """

    def __init__(self, tables):
        """
        Initialize DuckDB connection with data from multiple tables.

        Args:
            tables (dict): Dictionary where keys are table names and values are arrays of dictionaries
        """
        self.connection = duckdb.connect(database=":memory:")
        self.tables = {}

        # Register each table
        for table_name, data in tables.items():
            # Convert array of objects to pandas DataFrame
            df = pd.DataFrame(data)
            self.tables[table_name] = df

            # Register the DataFrame as a table in DuckDB
            self.connection.register(table_name, df)

    def execute(
        self,
        query,
        params=None,
        as_dict=False,
        pluck=None,
        first=False,
        pick=None,
        omit=None,
    ):
        """
        Execute a SQL query and return the results.

        Args:
            query (str): SQL query to execute (use ? for parameters)
            params (list, optional): Parameters to bind to the query
            as_dict (bool, optional): Return results as list of dicts instead of tuples (default: False)
            pluck (str, optional): Column name to extract as an array. Mutually exclusive with pick/omit.
            first (bool, optional): Return only the first result instead of a list (default: False)
            pick (list, optional): Array of column names to include. Mutually exclusive with pluck/omit.
            omit (list, optional): Array of column names to exclude. Mutually exclusive with pluck/pick.

        Returns:
            Results vary based on parameters:
            - Default: list of tuples [(col1, col2, ...), ...]
            - as_dict=True: list of dicts [{"col1": val1, ...}, ...]
            - pluck="col": list of values [val1, val2, ...]
            - first=True: single tuple, dict, or value (or None if no results)
            - pick/omit: filters columns before returning tuples or dicts

        Processing order:
            1. Execute query
            2. Apply pluck (if specified) - extracts single column
            3. Apply pick/omit (if specified) - filters columns
            4. Apply as_dict (if True) - converts tuples to dicts
            5. Apply first (if True) - returns first result only

        Examples:
            # Basic queries
            db.execute("SELECT * FROM people WHERE age > ?", [28])
            # [("John", 30, "New York"), ("Bob", 35, "Chicago")]

            db.execute("SELECT * FROM people", as_dict=True)
            # [{"name": "John", "age": 30, "city": "New York"}, ...]

            # Extract single column
            db.execute("SELECT name FROM people", pluck="name")
            # ["John", "Jane", "Bob"]

            # Get first result
            db.execute("SELECT * FROM people WHERE id = ?", [1], as_dict=True, first=True)
            # {"name": "John", "age": 30, "city": "New York"}

            # Get single value
            db.execute("SELECT name FROM people WHERE id = ?", [1], pluck="name", first=True)
            # "John"

            # Filter columns (tuples)
            db.execute("SELECT * FROM people", pick=["name", "age"])
            # [("John", 30), ("Jane", 25), ("Bob", 35)]

            # Filter columns (dicts)
            db.execute("SELECT * FROM people", as_dict=True, pick=["name", "age"])
            # [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]

            # Exclude columns
            db.execute("SELECT * FROM people", as_dict=True, omit=["id", "created_at"])
            # Returns all columns except 'id' and 'created_at'

            # Join multiple tables
            db.execute(\"\"\"
                SELECT p.name, p.age, c.population
                FROM people p
                JOIN cities c ON p.city = c.name
                WHERE p.age > ?
            \"\"\", [25], as_dict=True)
        """
        result = self.connection.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.connection.description]

        if pluck:
            if pluck not in columns:
                raise ValueError(f"Column '{pluck}' not found in query results")
            col_index = columns.index(pluck)
            result = [row[col_index] for row in result]

        # Apply pick/omit filtering
        elif pick or omit:
            if pick:
                # Select only specified columns
                indices = [i for i, col in enumerate(columns) if col in pick]
                columns = [columns[i] for i in indices]
            else:  # omit
                # Exclude specified columns
                indices = [i for i, col in enumerate(columns) if col not in omit]
                columns = [columns[i] for i in indices]

            # Filter tuple values based on selected indices
            result = [tuple(row[i] for i in indices) for row in result]

        if as_dict:
            result = [dict(zip(columns, row)) for row in result]

        if first:
            return result[0] if result else None

        return result

    def execute_df(self, query, params=None):
        """
        Execute a SQL query and return the results as a pandas DataFrame.

        Args:
            query (str): SQL query to execute (use ? for parameters)
            params (list, optional): Parameters to bind to the query

        Returns:
            pd.DataFrame: Query results as a DataFrame

        Example:
            db.execute_df("SELECT * FROM people WHERE age > ?", [28])
        """
        return self.connection.execute(query, params).df()

    def close(self):
        """Close the DuckDB connection."""
        self.connection.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the connection."""
        self.close()


def make_queryable(tables):
    """
    Create a DuckDBQueryable instance from a dictionary of tables.

    This is a convenience function for creating a DuckDB helper.

    Args:
        tables (dict): Dictionary where keys are table names and values are arrays of dictionaries

    Returns:
        DuckDBQueryable: Initialized DuckDB helper instance

    Examples:
        # Basic usage
        tables = {
            "people": [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}],
            "cities": [{"name": "New York", "population": 8000000}]
        }
        db = make_queryable(tables)
        results = db.execute("SELECT * FROM people WHERE age > ?", [28])
        db.close()

        # Using context manager (recommended)
        with make_queryable(tables) as db:
            results = db.execute("SELECT * FROM people WHERE age > ?", [28])
            # Automatically closes connection
    """
    return DuckDBQueryable(tables)
