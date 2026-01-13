# Examples

Comprehensive examples for OpenObserve API integration across different contexts and use cases.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Integration Contexts](#integration-contexts)
3. [Common Use Cases](#common-use-cases)

## Basic Usage

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
    sql="SELECT * FROM application_logs",
    start_time="2025-12-26T00:00:00Z",
    end_time="2025-12-26T23:59:59Z",
    size=100
)

if result["success"]:
    logs = result["response"]
    for log in logs.get("hits", []):
        print(log)
```

## Integration Contexts

### From Server Scripts

Use the safe_exec global directly:

```python
# Send logs from Server Script
open_observe.send_logs(
    stream="server-script-logs",
    logs=[{
        "message": "Server script executed",
        "script_name": "My Server Script",
        "user": frappe.session.user,
        "timestamp": frappe.utils.now()
    }]
)

# Search logs from Server Script
results = open_observe.search_logs(
    sql="SELECT * FROM server_script_logs",
    start_time="2025-12-26T00:00:00Z",
    end_time="2025-12-26T23:59:59Z"
)
```

### From Business Logic

```python
# In a Business Logic script
open_observe.send_logs(
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
// Send logs
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

// Search logs
frappe.call({
    method: 'tweaks.tweaks.doctype.open_observe_api.open_observe_api.search_logs',
    args: {
        sql: 'SELECT * FROM client_events',
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

### From Document Hooks

```python
# In hooks.py
doc_events = {
    "Sales Order": {
        "after_save": "myapp.hooks.log_sales_order_changes"
    }
}

# In myapp/hooks.py
def log_sales_order_changes(doc, method):
    open_observe.send_logs(
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

## Common Use Cases

### Document Change Tracking

Track changes to important documents with detailed field-level changes:

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
        
        open_observe.send_logs(
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

### Error Logging with Traceback

Capture detailed error information for debugging:

```python
# In error handling
try:
    # Some operation that might fail
    process_complex_operation()
except Exception as e:
    open_observe.send_logs(
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

### Performance Monitoring

Track operation execution times:

```python
import time

start_time = time.time()

# Do some work
process_data()

duration = time.time() - start_time

open_observe.send_logs(
    stream="performance-metrics",
    logs=[{
        "operation": "process_data",
        "duration_seconds": duration,
        "timestamp": frappe.utils.now()
    }]
)
```

### User Activity Tracking

Monitor user actions and login events:

```python
# After user login
open_observe.send_logs(
    stream="user-activity",
    logs=[{
        "event": "login",
        "user": frappe.session.user,
        "ip_address": frappe.local.request_ip,
        "timestamp": frappe.utils.now()
    }]
)
```

### Log Analysis and Pattern Detection

Search and analyze logs to find patterns:

```python
# Search for errors in the last 24 hours
from datetime import datetime, timedelta

end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)

result = open_observe.search_logs(
    sql="SELECT * FROM application_errors",
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

### Complete Audit Trail

Implement comprehensive audit trail for compliance:

```python
# Register as a hook in hooks.py
doc_events = {
    "*": {
        "after_insert": "myapp.audit.log_insert",
        "on_update": "myapp.audit.log_update",
        "on_trash": "myapp.audit.log_delete"
    }
}

# In myapp/audit.py
def log_insert(doc, method):
    open_observe.send_logs(
        stream="audit-trail",
        logs=[{
            "action": "insert",
            "doctype": doc.doctype,
            "name": doc.name,
            "user": frappe.session.user,
            "timestamp": frappe.utils.now()
        }]
    )

def log_update(doc, method):
    if hasattr(doc, "_doc_before_save"):
        changes = get_changes(doc, doc._doc_before_save)
        if changes:
            open_observe.send_logs(
                stream="audit-trail",
                logs=[{
                    "action": "update",
                    "doctype": doc.doctype,
                    "name": doc.name,
                    "changes": changes,
                    "user": frappe.session.user,
                    "timestamp": frappe.utils.now()
                }]
            )

def log_delete(doc, method):
    open_observe.send_logs(
        stream="audit-trail",
        logs=[{
            "action": "delete",
            "doctype": doc.doctype,
            "name": doc.name,
            "user": frappe.session.user,
            "timestamp": frappe.utils.now()
        }]
    )

def get_changes(new_doc, old_doc):
    changes = {}
    for field in new_doc.meta.get_valid_columns():
        old_value = getattr(old_doc, field, None)
        new_value = getattr(new_doc, field, None)
        if old_value != new_value:
            changes[field] = {
                "old": old_value,
                "new": new_value
            }
    return changes
```

### Batch Processing with Progress Tracking

Log batch operation progress:

```python
def process_batch(items):
    open_observe.send_logs(
        stream="batch-processing",
        logs=[{
            "message": "Batch started",
            "total_items": len(items),
            "timestamp": frappe.utils.now()
        }]
    )
    
    processed = 0
    errors = 0
    
    for item in items:
        try:
            process_item(item)
            processed += 1
        except Exception as e:
            errors += 1
            open_observe.send_logs(
                stream="batch-processing",
                logs=[{
                    "message": f"Error processing item {item}",
                    "error": str(e),
                    "level": "error",
                    "timestamp": frappe.utils.now()
                }]
            )
    
    open_observe.send_logs(
        stream="batch-processing",
        logs=[{
            "message": "Batch completed",
            "processed": processed,
            "errors": errors,
            "timestamp": frappe.utils.now()
        }]
    )
```

### API Rate Limiting and Monitoring

Track API usage and monitor rate limits:

```python
def api_call_with_logging(endpoint, method="GET", **kwargs):
    start_time = time.time()
    
    try:
        response = requests.request(method, endpoint, **kwargs)
        duration = time.time() - start_time
        
        open_observe.send_logs(
            stream="api-monitoring",
            logs=[{
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "duration_seconds": duration,
                "timestamp": frappe.utils.now()
            }]
        )
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        
        open_observe.send_logs(
            stream="api-monitoring",
            logs=[{
                "endpoint": endpoint,
                "method": method,
                "error": str(e),
                "duration_seconds": duration,
                "level": "error",
                "timestamp": frappe.utils.now()
            }]
        )
        raise
```
