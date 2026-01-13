# API Reference

Complete documentation for OpenObserve API integration functions.

## send_logs(stream, logs, org=None)

Send logs to an OpenObserve stream.

**Parameters:**
- `stream` (str, required): Stream name to send logs to
- `logs` (list, required): List of log dictionaries to send
- `org` (str, optional): Organization name (uses default_org if not provided)

**Returns:**
```python
{
    "success": bool,
    "response": dict,  # OpenObserve API response
    "status_code": int
}
```

**Permissions:** System Manager only

**Examples:**
```python
# Single log entry
result = send_logs(
    stream="application-logs",
    logs=[{
        "message": "User login successful",
        "level": "info",
        "user": "john@example.com",
        "timestamp": "2025-12-26T02:20:00Z"
    }]
)

# Multiple logs with custom organization
result = send_logs(
    stream="error-logs",
    logs=[
        {"message": "Error occurred", "level": "error", "code": 500},
        {"message": "Retry failed", "level": "error", "code": 503}
    ],
    org="production"
)
```

## search_logs(stream, query=None, org=None, start_time=None, end_time=None, size=100)

Search logs from an OpenObserve stream.

**Parameters:**
- `stream` (str, required): Stream name to search logs from
- `query` (dict, optional): SQL query or query object for filtering logs
- `org` (str, optional): Organization name (uses default_org if not provided)
- `start_time` (str, optional): Start time in ISO format (e.g., "2025-12-26T05:00:00Z"). Auto-converted to Unix microseconds
- `end_time` (str, optional): End time in ISO format (e.g., "2025-12-26T06:00:00Z"). Auto-converted to Unix microseconds
- `size` (int, optional): Maximum number of logs to return (default: 100)

**Returns:**
```python
{
    "success": bool,
    "response": dict,  # Search results with "hits" array
    "status_code": int
}
```

**Permissions:** System Manager only

**Examples:**
```python
# Time-based search
result = search_logs(
    stream="application-logs",
    start_time="2025-12-26T05:00:00Z",
    end_time="2025-12-26T06:00:00Z",
    size=50
)

# SQL query
result = search_logs(
    stream="error-logs",
    query={"sql": "SELECT * FROM error_logs WHERE level='error'"},
    size=100
)

# JSON filter with bool query
result = search_logs(
    stream="sales-orders",
    query={
        "query": {
            "bool": {
                "must": [
                    {"term": {"status": "completed"}},
                    {"range": {"grand_total": {"gte": 1000}}}
                ]
            }
        }
    },
    org="production"
)
```

## test_connection()

Test connection to OpenObserve API by sending a test log entry.

**Returns:**
```python
{
    "success": bool,
    "message": str,
    "details": dict,  # If successful
    "error": str      # If failed
}
```

**Example:**
```python
result = test_connection()
if result["success"]:
    print("Connection successful!")
else:
    print(f"Connection failed: {result['error']}")
```

## Configuration Methods

### validate_setup()

Validates OpenObserve API configuration.

**Raises:** `frappe.ValidationError` if configuration is invalid (missing URL, user, or password)

**Example:**
```python
config = frappe.get_doc("Open Observe API", "Open Observe API")
config.validate_setup()  # Raises error if invalid
```

## API Endpoint Formats

**Send Logs:**
```
{url}/api/{org}/{stream}/_json
```

**Search Logs:**
```
{url}/api/{org}/{stream}/_search
```

**Example:**
```
https://api.openobserve.ai/api/default/application-logs/_json
https://api.openobserve.ai/api/default/application-logs/_search
```

## Error Handling

All API calls include:
- Configuration validation (missing fields)
- HTTP error catching and logging
- Error logging to Frappe Error Log
- User-friendly error messages
- 30-second timeout

**Example:**
```python
try:
    send_logs("my-stream", [{"message": "test"}])
except Exception as e:
    # Error is logged and user-friendly message is displayed
    print(f"Failed: {e}")
```
