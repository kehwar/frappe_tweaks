# Integration Examples

Usage examples for different integration contexts.

## From Python Code

### Send Single Log Entry

```python
import frappe

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

### Send Multiple Logs

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

### Search Logs

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

## From Server Scripts

Use the safe_exec global directly:

```python
# Send logs from Server Script
frappe.open_observe.send_logs(
    stream="server-script-logs",
    logs=[{
        "message": "Server script executed",
        "script_name": "My Server Script",
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }]
)

# Search logs from Server Script
results = frappe.open_observe.search_logs(
    stream="server-script-logs",
    start_time="2025-12-26T00:00:00Z",
    end_time="2025-12-26T23:59:59Z"
)
```

## From Business Logic

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

## From JavaScript (Client-side)

### Send Logs

```javascript
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

### Search Logs

```javascript
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

## From Document Hooks

### Document Changes Hook

```python
# In hooks.py
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

## Safe Exec Global Reference

Available in Server Scripts and Business Logic:

```python
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
