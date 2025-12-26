# OpenObserve API Usage Examples

This document shows examples of how to use the OpenObserve API integration.

## Configuration

First, configure the OpenObserve API settings:

1. Navigate to: **Open Observe API** in Frappe
2. Set the following fields:
   - **URL**: Your OpenObserve instance URL (e.g., `https://api.openobserve.ai`)
   - **User**: Your username/email
   - **Password**: Your password
   - **Default Organization**: (optional) Default organization name

## Using from Python Code

### Send a single log entry

```python
import frappe

# Send a single log entry
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

### Send multiple logs

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

### Send logs to a specific organization

```python
import frappe

result = frappe.call(
    "tweaks.tweaks.doctype.open_observe_api.open_observe_api.send_logs",
    stream="production-logs",
    logs=[{"message": "Production event", "level": "info"}],
    org="production"
)
```

## Using from Server Scripts

In Server Scripts, you can use the safe_exec global:

```python
# Send logs directly from a Server Script
frappe.open_observe_api.send_logs(
    stream="server-script-logs",
    logs=[{
        "message": "Server script executed",
        "script_name": "My Server Script",
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }]
)
```

## Using from Business Logic

```python
# In a Business Logic script
frappe.open_observe_api.send_logs(
    stream="business-logic",
    logs=[{
        "message": "Business logic executed",
        "doctype": doc.doctype,
        "name": doc.name,
        "action": "validate"
    }]
)
```

## Using from JavaScript (Client-side)

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
    frappe.open_observe_api.send_logs(
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

### 2. Logging Errors

```python
try:
    # Some operation that might fail
    process_complex_operation()
except Exception as e:
    frappe.open_observe_api.send_logs(
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

frappe.open_observe_api.send_logs(
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
frappe.open_observe_api.send_logs(
    stream="user-activity",
    logs=[{
        "event": "login",
        "user": frappe.session.user,
        "ip_address": frappe.local.request_ip,
        "timestamp": frappe.utils.now()
    }]
)
```

## Testing Connection

To test if your configuration is correct:

1. Open the **Open Observe API** doctype
2. Click the **Test Connection** button
3. Check the response message

Or programmatically:

```python
import frappe

result = frappe.call(
    "tweaks.tweaks.doctype.open_observe_api.open_observe_api.test_connection"
)

if result.get("success"):
    print("Connection successful!")
else:
    print(f"Connection failed: {result.get('error')}")
```

## Important Notes

1. Only **System Managers** can send logs to OpenObserve
2. All passwords are stored securely using Frappe's password encryption
3. API calls have a 30-second timeout
4. Errors are automatically logged to Frappe's Error Log
5. Logs can contain any fields - OpenObserve will index them all

## Troubleshooting

### Error: "Permission Denied"
- Make sure the user has the System Manager role

### Error: "URL is required"
- Check that the Open Observe API configuration is complete

### Error: "Connection timeout"
- Check network connectivity to your OpenObserve instance
- Verify the URL is correct

### Error: "Authentication failed"
- Verify your username and password are correct
- Check that the user has permissions in OpenObserve
