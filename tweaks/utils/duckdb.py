"""
DuckDB utilities for frappe_tweaks

This module provides helper functions for working with DuckDB, an in-memory analytical
database that can be used for fast SQL queries on various data sources.
"""

import duckdb
import frappe


class DuckDBData:
    """
    A wrapper class for working with DuckDB connections.

    This class provides a convenient interface for loading data into DuckDB
    and executing SQL queries against it.

    Example:
        >>> data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        >>> duckdata = load(data)
        >>> result = duckdata.query("SELECT * FROM data WHERE age > 26")
        >>> print(result)
    """

    def __init__(self, connection):
        """
        Initialize DuckDBData with a connection.

        Args:
            connection: A DuckDB connection object
        """
        self.connection = connection

    def query(self, sql, *args, **kwargs):
        """
        Execute a SQL query and return results.

        Args:
            sql (str): The SQL query to execute
            *args: Positional arguments to pass to the query
            **kwargs: Keyword arguments to pass to the query

        Returns:
            duckdb.DuckDBPyRelation: Query result that can be converted to various formats

        Example:
            >>> result = duckdata.query("SELECT * FROM data WHERE age > ?", 25)
            >>> df = result.df()  # Convert to pandas DataFrame
            >>> list_result = result.fetchall()  # Get as list
        """
        try:
            return self.connection.execute(sql, *args, **kwargs)
        except Exception as e:
            frappe.throw(f"DuckDB query failed: {str(e)}", title="Query Error")

    def close(self):
        """
        Close the DuckDB connection.
        """
        if self.connection:
            self.connection.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def load(data, table_name="data"):
    """
    Load data into an in-memory DuckDB database.

    This function creates a new DuckDB connection and loads the provided data
    into a table that can be queried using SQL.

    Args:
        data: The data to load. Can be:
            - List of dictionaries
            - Pandas DataFrame
            - Dictionary mapping column names to lists
            - Any other format supported by DuckDB
        table_name (str, optional): Name of the table to create. Defaults to "data"

    Returns:
        DuckDBData: A DuckDBData instance that can be used to query the data

    Example:
        >>> # From list of dictionaries
        >>> data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        >>> duckdata = load(data)
        >>> result = duckdata.query("SELECT AVG(age) as avg_age FROM data")
        >>> print(result.fetchone())

        >>> # From pandas DataFrame
        >>> import pandas as pd
        >>> df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        >>> duckdata = load(df, table_name="my_table")
        >>> result = duckdata.query("SELECT SUM(x) FROM my_table")
    """
    if data is None:
        frappe.throw("Data cannot be None", title="Invalid Data")

    try:
        # Create an in-memory DuckDB connection
        conn = duckdb.connect(":memory:")

        # Load data into DuckDB
        # DuckDB can automatically infer the schema from various data types
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # List of dictionaries
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM data")
        elif hasattr(data, "to_dict"):
            # Pandas DataFrame or similar
            conn.register(table_name, data)
        elif isinstance(data, dict):
            # Dictionary of lists
            conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM data")
        else:
            # Try to register as-is
            conn.register(table_name, data)

        return DuckDBData(conn)

    except Exception as e:
        frappe.throw(
            f"Failed to load data into DuckDB: {str(e)}",
            title="Data Load Error",
        )
