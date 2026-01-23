---
name: report-long-polling
description: Expert guidance for implementing long-running report execution using Frappe Tweaks report_long_polling API. Use when integrating external systems (Power Query, Power BI, third-party apps) with Frappe reports, implementing asynchronous report execution with polling, avoiding timeout issues with large reports, creating prepared reports via API, checking job status with polling, retrieving report results after completion, or working with tweaks.utils.report_long_polling module endpoints.
---

# Report Long Polling

Expert guidance for implementing asynchronous report execution using the Frappe Tweaks report_long_polling API.

## Overview

The report_long_polling module (`tweaks.utils.report_long_polling`) provides a three-endpoint API for executing long-running Frappe reports asynchronously:

1. **start_job** - Create a Prepared Report job
2. **CHECK STATUS** - Poll job status with configurable attempts and sleep
3. **get_result** - Retrieve completed report data

This pattern prevents timeouts on large reports and enables integration with external systems like Power Query, Power BI, or other third-party applications.

## API Endpoints

### 1. Start Job

**Endpoint:** `/api/method/tweaks.utils.report_long_polling.start_job`

**Purpose:** Create a new Prepared Report job

**Parameters:**
- `report_name` (required): Name of the Frappe report to execute
- `**kwargs`: Report filters (optional, varies by report)

**Returns:** Job ID (Prepared Report name)

**Example:**
```
GET /api/method/tweaks.utils.report_long_polling.start_job?report_name=Item%20Prices
```

**Response:**
```json
{
    "message": "prep-report-job-id-12345"
}
```

### 2. CHECK STATUS

**Endpoint:** `/api/method/tweaks.utils.report_long_polling.check_status`

**Purpose:** Poll job status with built-in retry logic

**Parameters:**
- `job_id` (required): Job ID from start_job
- `attempts` (optional): Max polling attempts (default: 2)
- `sleep` (optional): Seconds between attempts (default: 5)

**Returns:** 1 if completed/error, 0 if still running

**Example:**
```
GET /api/method/tweaks.utils.report_long_polling.check_status?job_id=prep-report-job-id-12345&attempts=2&sleep=5
```

**Response:**
```json
{
    "message": 1
}
```

**Behavior:**
- Polls up to `attempts` times with `sleep` seconds between attempts
- Returns 1 if status is "Completed" or "Error"
- Returns 1 if job not found (DoesNotExistError)
- Returns 0 if still running after all attempts

### 3. Get Result

**Endpoint:** `/api/method/tweaks.utils.report_long_polling.get_result`

**Purpose:** Retrieve completed report data

**Parameters:**
- `job_id` (required): Job ID from start_job

**Returns:** Report result with columns metadata and data rows

**Example:**
```
GET /api/method/tweaks.utils.report_long_polling.get_result?job_id=prep-report-job-id-12345
```

**Response:**
```json
{
    "message": {
        "columns": [
            {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Link"},
            {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data"},
            {"fieldname": "price_list_rate", "label": "Rate", "fieldtype": "Currency"}
        ],
        "result": [
            {"item_code": "ITEM-001", "item_name": "Product A", "price_list_rate": 100.00},
            {"item_code": "ITEM-002", "item_name": "Product B", "price_list_rate": 250.00}
        ]
    }
}
```

**Error Cases:**
- Status "Error": Returns empty columns/result with error message
- Job not found: Returns empty columns/result with "not found" message
- Still processing: Returns empty columns/result with "still generating" message

## Workflow Pattern

The typical integration workflow:

1. **Start the job** - Call `start_job` with report name and filters
2. **Poll for completion** - Repeatedly call `check_status` until it returns 1
3. **Retrieve results** - Call `get_result` to get the report data

**Important:** Always poll `CHECK STATUS` before calling `get_result`. The CHECK STATUS endpoint has built-in polling logic that waits for completion, reducing API calls.

## Integration Guidelines

### Power Query Integration

For Power Query M code integration, see [references/power-query-example.md](references/power-query-example.md).

Key considerations:
- Use cache-busting with timestamps to prevent Power Query caching
- Implement recursive polling with max attempts safeguard
- Apply column types based on Frappe fieldtype metadata
- Reorder columns to match report definition order

### General External System Integration

When integrating with any external system:

1. **Authentication**: Use Frappe API key/secret or session-based auth
2. **Error handling**: Check for error status in responses
3. **Timeout management**: Configure appropriate max attempts for your use case
4. **Result processing**: Parse columns metadata to properly type result data

### Column Metadata

The `columns` array in the result provides metadata for each column:

- `fieldname`: Database field name
- `label`: Display label (use for column headers)
- `fieldtype`: Frappe field type (Int, Data, Date, Currency, etc.)

Use this metadata to:
- Apply proper data types to result columns
- Rename columns with user-friendly labels
- Reorder columns to match report definition

## Implementation Location

The report_long_polling module is located at:
```
tweaks/utils/report_long_polling.py
```

The module uses Frappe's native Prepared Report system:
- `frappe.core.doctype.prepared_report.prepared_report.make_prepared_report`
- `frappe.desk.query_report.get_prepared_report_result`

## Use Cases

- **Large reports**: Reports with thousands of rows that exceed standard timeout limits
- **External BI tools**: Power BI, Tableau, or other tools that need async data access
- **Scheduled jobs**: Automated report generation for downstream processing
- **Third-party integrations**: API consumers that need reliable report data access
- **Custom dashboards**: External dashboards pulling Frappe report data

## Troubleshooting

**Job stays in "Queued" status:**
- Check that background workers are running (`bench worker`)
- Verify report permissions for the API user
- Check for errors in background worker logs

**Empty or incomplete results:**
- Ensure check_status returned 1 before calling get_result
- Verify job_id matches the one returned by start_job
- Check prepared report document for error status

**Performance issues:**
- Adjust `attempts` and `sleep` parameters based on report complexity
- Consider report optimization if consistently timing out
- Monitor Prepared Report queue depth
