---
description: 'Guidelines for working with OpenObserve API integration in Frappe Tweaks'
applyTo: '**/open_observe_api/**/*.py, **/open_observe_api/**/*.js, **/open_observe_api/**/*.json'
---

# OpenObserve API Integration

Guidelines for working with the OpenObserve API integration in Frappe Tweaks. OpenObserve is an open-source observability platform for logs, metrics, and traces.

## Project Context

- **Technology**: Frappe Framework (Python + JavaScript)
- **Integration Type**: REST API with Basic Authentication
- **API Documentation**: https://openobserve.ai/docs/
- **DocType**: Single DocType (Open Observe API)
- **Module**: Tweaks

## Overview

The OpenObserve API integration provides functionality to send logs from Frappe applications to OpenObserve streams for monitoring and analysis. The integration is restricted to System Managers for security.

## Configuration

### Required Fields

- **URL** (required): Base URL of the OpenObserve instance (e.g., `https://api.openobserve.ai`)
- **User** (required): Username/email for authentication
- **Password** (required): Password for authentication (stored securely)
- **Default Organization** (optional): Default organization name to use when not specified

### Example Configuration

```python
doc = frappe.get_doc("Open Observe API", "Open Observe API")
doc.url = "https://api.openobserve.ai"
doc.user = "admin@example.com"
doc.password = "secure_password"
doc.default_org = "default"
doc.save()
```

## API Functions

### send_logs(stream, logs, org=None)

Send logs to an OpenObserve stream.

**Parameters:**
- `stream` (str): Stream name to send logs to
- `logs` (list): List of log dictionaries to send
- `org` (str, optional): Organization name (uses default_org if not provided)

**Returns:**
- Dictionary with `success`, `response`, and `status_code`

**Permissions:**
- Only System Managers can call this function

**Example Usage:**

```python
# Send a single log entry
result = send_logs(
    stream="application-logs",
    logs=[{
        "message": "User login successful",
        "level": "info",
        "user": "john@example.com",
        "timestamp": "2025-12-26T02:20:00Z"
    }]
)

# Send multiple logs with custom organization
result = send_logs(
    stream="error-logs",
    logs=[
        {"message": "Error occurred", "level": "error", "code": 500},
        {"message": "Retry failed", "level": "error", "code": 503}
    ],
    org="production"
)
```

### search_logs(stream, query=None, org=None, start_time=None, end_time=None, size=100)

Search logs from an OpenObserve stream.

**Parameters:**
- `stream` (str): Stream name to search logs from
- `query` (dict, optional): SQL query or query object for filtering logs
- `org` (str, optional): Organization name (uses default_org if not provided)
- `start_time` (str, optional): Start time for log search in ISO format
- `end_time` (str, optional): End time for log search in ISO format
- `size` (int, optional): Maximum number of logs to return (default: 100)

**Returns:**
- Dictionary with `success`, `response`, and `status_code`

**Permissions:**
- Only System Managers can call this function

**Example Usage:**

```python
# Search logs from last hour
result = search_logs(
    stream="application-logs",
    start_time="2025-12-26T05:00:00Z",
    end_time="2025-12-26T06:00:00Z",
    size=50
)

# Search with custom SQL query
result = search_logs(
    stream="error-logs",
    query={"sql": "SELECT * FROM error_logs WHERE level='error'"},
    size=100
)

# Search with filters
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

### test_connection()

Test connection to OpenObserve API by sending a test log entry.

**Returns:**
- Dictionary with `success`, `message`, and optional `details` or `error`

**Example Usage:**

```python
result = test_connection()
if result["success"]:
    print("Connection successful!")
else:
    print(f"Connection failed: {result['error']}")
```

## Usage Examples

### From Python Code

#### Send a single log entry

```python
import frappe

# Direct call
result = frappe.call(
    "tweaks.tweaks.doctype.open_observe_api.open_observe_api.send_logs",
    stream="application-logs",
    logs=[{
        "message": "User login successful",
        "level": "info",
        "user": "john@example.com",
        "timestamp": frappe.utils.now()
    }]
)
```

#### Send multiple logs

```python
import frappe

logs = [
    {"message": "Process started", "level": "info", "step": 1},
    {"message": "Processing item 1", "level": "info", "step": 2},
    {"message": "Processing item 2", "level": "info", "step": 3},
    {"message": "Process completed", "level": "info", "step": 4}
]

result = frappe.call(
    "tweaks.tweaks.doctype.open_observe_api.open_observe_api.send_logs",
    stream="batch-processing",
    logs=logs
)
```

#### Search logs

```python
import frappe

# Search logs from a specific time range
result = frappe.call(
    "tweaks.tweaks.doctype.open_observe_api.open_observe_api.search_logs",
    stream="application-logs",
    start_time="2025-12-26T00:00:00Z",
    end_time="2025-12-26T23:59:59Z",
    size=100
)

if result["success"]:
    logs = result["response"]
    for log in logs.get("hits", []):
        print(log)
```

### From Server Scripts

In Server Scripts, you can use the safe_exec global:

```python
# Send logs directly from a Server Script
frappe.open_observe.send_logs(
    stream="server-script-logs",
    logs=[{
        "message": "Server script executed",
        "script_name": "My Server Script",
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }]
)

# Search logs from a Server Script
results = frappe.open_observe.search_logs(
    stream="server-script-logs",
    start_time="2025-12-26T00:00:00Z",
    end_time="2025-12-26T23:59:59Z"
)
```

### From Business Logic

```python
# In a Business Logic script
frappe.open_observe.send_logs(
    stream="business-logic",
    logs=[{
        "message": "Business logic executed",
        "doctype": doc.doctype,
        "name": doc.name,
        "action": "validate"
    }]
)
```

### From JavaScript (Client-side)

```javascript
// Send logs from client-side
frappe.call({
    method: 'tweaks.tweaks.doctype.open_observe_api.open_observe_api.send_logs',
    args: {
        stream: 'client-events',
        logs: [{
            message: 'Form submitted',
            level: 'info',
            user: frappe.session.user,
            timestamp: frappe.datetime.now_datetime()
        }]
    },
    callback: function(r) {
        if (r.message && r.message.success) {
            console.log('Logs sent successfully');
        }
    }
});

// Search logs from client-side
frappe.call({
    method: 'tweaks.tweaks.doctype.open_observe_api.open_observe_api.search_logs',
    args: {
        stream: 'client-events',
        start_time: '2025-12-26T00:00:00Z',
        end_time: '2025-12-26T23:59:59Z',
        size: 50
    },
    callback: function(r) {
        if (r.message && r.message.success) {
            console.log('Search results:', r.message.response);
        }
    }
});
```

## Safe Exec Global

The OpenObserve API is available in safe_exec contexts (Server Scripts, Business Logic, etc.) via:

```python
# In Server Scripts or Business Logic

# Send logs
frappe.open_observe.send_logs(
    stream="my-stream",
    logs=[{"message": "Test log", "level": "info"}]
)

# Search logs
results = frappe.open_observe.search_logs(
    stream="my-stream",
    start_time="2025-12-26T00:00:00Z",
    end_time="2025-12-26T23:59:59Z"
)
```

## Security Considerations

- Only System Managers can send logs to OpenObserve
- Password is stored securely using Frappe's password field encryption
- Authentication uses HTTP Basic Auth with base64-encoded credentials
- All API calls include timeout (30 seconds) to prevent hanging
- Errors are logged using Frappe's error logging system

## Error Handling

The integration includes comprehensive error handling:

1. **Configuration Validation**: Checks for missing required fields
2. **HTTP Errors**: Catches and logs request exceptions
3. **Error Logging**: All errors are logged to Frappe Error Log
4. **User Feedback**: Meaningful error messages are shown to users

### Example Error Response

```python
try:
    send_logs("my-stream", [{"message": "test"}])
except Exception as e:
    # Error is logged and user-friendly message is displayed
    print(f"Failed: {e}")
```

## API Endpoint Formats

OpenObserve API endpoint formats:

**Send Logs:**
```
{url}/api/{org}/{stream}/_json
```

**Search Logs:**
```
{url}/api/{org}/{stream}/_search
```

Example:
```
https://api.openobserve.ai/api/default/application-logs/_json
https://api.openobserve.ai/api/default/application-logs/_search
```

## Testing

The doctype includes test cases in `test_open_observe_api.py`:

- Configuration validation
- Authentication header generation
- API integration (requires live connection)

Run tests:
```bash
bench --site development.localhost run-tests --app tweaks --doctype "Open Observe API"
```

## Client-Side Integration

The doctype includes a JavaScript file with a "Test Connection" button:

```javascript
frappe.ui.form.on('Open Observe API', {
    refresh: function(frm) {
        // Test Connection button is automatically added
    }
});
```

## Common Use Cases

### 1. Logging Document Changes

```python
# In a document hook (hooks.py)
doc_events = {
    "Sales Order": {
        "after_save": "myapp.hooks.log_sales_order_changes"
    }
}

# In myapp/hooks.py
def log_sales_order_changes(doc, method):
    frappe.open_observe.send_logs(
        stream="sales-order-changes",
        logs=[{
            "doctype": doc.doctype,
            "name": doc.name,
            "grand_total": doc.grand_total,
            "status": doc.status,
            "customer": doc.customer,
            "user": frappe.session.user,
            "timestamp": frappe.utils.now()
        }]
    )
```

### 2. Logging Errors with Traceback

```python
# In error handling
try:
    # Some operation that might fail
    process_complex_operation()
except Exception as e:
    frappe.open_observe.send_logs(
        stream="application-errors",
        logs=[{
            "message": str(e),
            "level": "error",
            "traceback": frappe.get_traceback(),
            "user": frappe.session.user,
            "timestamp": frappe.utils.now()
        }]
    )
    raise
```

### 3. Performance Monitoring

```python
import time

start_time = time.time()

# Do some work
process_data()

duration = time.time() - start_time

frappe.open_observe.send_logs(
    stream="performance-metrics",
    logs=[{
        "operation": "process_data",
        "duration_seconds": duration,
        "timestamp": frappe.utils.now()
    }]
)
```

### 4. User Activity Tracking

```python
# After user login
frappe.open_observe.send_logs(
    stream="user-activity",
    logs=[{
        "event": "login",
        "user": frappe.session.user,
        "ip_address": frappe.local.request_ip,
        "timestamp": frappe.utils.now()
    }]
)
```

### 5. Searching and Analyzing Logs

```python
# Search for errors in the last 24 hours
from datetime import datetime, timedelta

end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)

result = frappe.open_observe.search_logs(
    stream="application-errors",
    start_time=start_time.isoformat() + "Z",
    end_time=end_time.isoformat() + "Z",
    size=100
)

if result["success"]:
    errors = result["response"]
    print(f"Found {len(errors.get('hits', []))} errors in the last 24 hours")
    
    # Analyze error patterns
    for error in errors.get('hits', []):
        print(f"Error: {error.get('message')} at {error.get('timestamp')}")
```

### 6. Audit Trail Implementation

```python
# In a document hook for audit logging
def log_document_changes(doc, method):
    """Log all changes to important documents"""
    if doc.doctype in ["Sales Invoice", "Purchase Order", "Payment Entry"]:
        # Get changes if updating
        changes = {}
        if method == "on_update" and hasattr(doc, "_doc_before_save"):
            old_doc = doc._doc_before_save
            for field in doc.meta.get_valid_columns():
                old_value = getattr(old_doc, field, None)
                new_value = getattr(doc, field, None)
                if old_value != new_value:
                    changes[field] = {
                        "old": old_value,
                        "new": new_value
                    }
        
        frappe.open_observe.send_logs(
            stream="audit-trail",
            logs=[{
                "doctype": doc.doctype,
                "name": doc.name,
                "action": method,
                "changes": changes,
                "user": frappe.session.user,
                "timestamp": frappe.utils.now()
            }]
        )
```

## Best Practices

1. **Use Descriptive Stream Names**: Use clear, hierarchical stream names (e.g., `app-errors`, `user-login`, `data-sync`)
2. **Include Timestamps**: Always include timestamps in log entries for proper time-series analysis
3. **Add Context**: Include relevant context (user, doctype, action) in log entries
4. **Batch When Possible**: Send multiple logs in a single request for efficiency
5. **Handle Errors Gracefully**: Don't let logging failures break your application
6. **Use Appropriate Log Levels**: Use standard levels (info, warning, error, debug)
7. **Respect Permissions**: Only System Managers can send logs - don't try to bypass this
8. **Use Search for Analytics**: Leverage search_logs to analyze patterns and trends in your logs

## Maintenance

### Updating Configuration

```python
doc = frappe.get_doc("Open Observe API", "Open Observe API")
doc.url = "https://new-url.openobserve.ai"
doc.save()
```

### Checking Configuration

```python
config = frappe.get_doc("Open Observe API", "Open Observe API")
config.validate_setup()  # Raises error if invalid
```

## Related Resources

- OpenObserve Documentation: https://openobserve.ai/docs/
- OpenObserve API Reference: https://openobserve.ai/docs/api/
- Frappe Framework: https://frappeframework.com/docs
- Safe Exec Documentation: See `.github/instructions/sync-job.instructions.md`
