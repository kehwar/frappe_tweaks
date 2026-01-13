# Common Use Cases

Implementation patterns for common logging and monitoring scenarios.

## 1. Logging Document Changes

Track changes to important documents:

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

## 2. Error Logging with Traceback

Capture detailed error information:

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

## 3. Performance Monitoring

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

## 4. User Activity Tracking

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

## 5. Searching and Analyzing Logs

Find patterns in logs over time:

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

## 6. Audit Trail Implementation

Complete audit trail for compliance:

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

## 7. Batch Processing Logs

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

## 8. API Rate Limiting Monitoring

Track API usage and rate limits:

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
