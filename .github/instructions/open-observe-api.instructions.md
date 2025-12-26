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

## Safe Exec Global

The OpenObserve API is available in safe_exec contexts (Server Scripts, Business Logic, etc.) via:

```python
# In Server Scripts or Business Logic
frappe.open_observe_api.send_logs(
    stream="my-stream",
    logs=[{"message": "Test log", "level": "info"}]
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

## API Endpoint Format

OpenObserve API endpoint format:
```
{url}/api/{org}/{stream}/_json
```

Example:
```
https://api.openobserve.ai/api/default/application-logs/_json
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

## Common Patterns

### Logging Application Events

```python
# In a document hook
def after_save(doc, method):
    if frappe.session.user == "System Manager":
        frappe.open_observe_api.send_logs(
            stream="document-changes",
            logs=[{
                "doctype": doc.doctype,
                "name": doc.name,
                "action": "saved",
                "user": frappe.session.user,
                "timestamp": frappe.utils.now()
            }]
        )
```

### Logging Errors

```python
# In error handling
try:
    # Some operation
    process_data()
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
```

### Batch Logging

```python
# Send multiple logs at once
logs = []
for item in items:
    logs.append({
        "item": item.name,
        "quantity": item.qty,
        "timestamp": frappe.utils.now()
    })

frappe.open_observe_api.send_logs(
    stream="batch-processing",
    logs=logs
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
