# Typst and DuckDB Utilities

This document provides examples of how to use the new typst and duckdb utilities in frappe_tweaks.

## Typst Utility

The `typst` utility allows you to generate PDF files from Typst markup.

### Usage in Server Scripts / Business Logic

```python
# Example 1: Basic PDF generation
typst_content = """
#set page(paper: "a4")
#set text(size: 11pt)

= Invoice

*Invoice Number:* 12345
*Date:* 2026-02-19

== Items
- Item 1: $100
- Item 2: $200

*Total:* $300
"""

file_doc = typst.make_pdf_file(typst_content, filename="invoice.pdf")
print(f"PDF created: {file_doc.file_url}")

# Example 2: Attach PDF to a document
typst_content = """
= Sales Order Summary

This is a summary for {doc.name}
"""

file_doc = typst.make_pdf_file(
    typst_content,
    filename="sales_order_summary.pdf",
    doctype="Sales Order",
    docname=doc.name
)
```

## DuckDB Utility

The `duckdb` utility allows you to perform SQL queries on in-memory data.

### Usage in Server Scripts / Business Logic

```python
# Example 1: Query a list of dictionaries
data = [
    {"customer": "Alice", "amount": 1000, "region": "North"},
    {"customer": "Bob", "amount": 1500, "region": "South"},
    {"customer": "Charlie", "amount": 800, "region": "North"},
]

duckdata = duckdb.load(data)

# Get total by region
result = duckdata.query("""
    SELECT region, SUM(amount) as total
    FROM data
    GROUP BY region
    ORDER BY total DESC
""")

for row in result.fetchall():
    print(f"Region: {row[0]}, Total: {row[1]}")

duckdata.close()

# Example 2: Filter and aggregate
data = frappe.get_all("Sales Invoice", 
    fields=["customer", "grand_total", "posting_date"],
    filters={"docstatus": 1}
)

duckdata = duckdb.load(data)

# Find top customers
result = duckdata.query("""
    SELECT customer, SUM(grand_total) as total
    FROM data
    WHERE posting_date >= '2026-01-01'
    GROUP BY customer
    ORDER BY total DESC
    LIMIT 10
""")

top_customers = result.fetchall()
duckdata.close()

# Example 3: Context manager (auto-close)
with duckdb.load(data) as duckdata:
    result = duckdata.query("SELECT COUNT(*) FROM data")
    count = result.fetchone()[0]
    print(f"Total records: {count}")

# Example 4: Join multiple data sources
orders = [
    {"order_id": 1, "customer_id": 100, "amount": 500},
    {"order_id": 2, "customer_id": 101, "amount": 750},
]

customers = [
    {"customer_id": 100, "name": "Alice"},
    {"customer_id": 101, "name": "Bob"},
]

# Load both datasets
duckdata = duckdb.load(orders, table_name="orders")
duckdata.connection.register("customers", customers)
duckdata.connection.execute("CREATE TABLE customers_table AS SELECT * FROM customers")

# Join the data
result = duckdata.query("""
    SELECT c.name, o.amount
    FROM orders o
    JOIN customers_table c ON o.customer_id = c.customer_id
""")

for row in result.fetchall():
    print(f"Customer: {row[0]}, Amount: {row[1]}")

duckdata.close()
```

## Installation

These utilities require external packages:

```bash
# Install typst (for PDF generation)
# On Ubuntu/Debian:
sudo apt-get install typst

# Or using cargo:
cargo install typst-cli

# Install duckdb (Python package)
pip install duckdb>=0.10.0

# Or in bench environment:
cd ~/frappe-bench
./env/bin/pip install duckdb>=0.10.0
```

## Notes

- Both utilities are available in the safe_exec environment for Server Scripts and Business Logic
- Typst requires the `typst` CLI tool to be installed on the system
- DuckDB works with pandas DataFrames, lists of dicts, and other common data structures
- DuckDB connections should be closed when done to free resources (or use context manager)
