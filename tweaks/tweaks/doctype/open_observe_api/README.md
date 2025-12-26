## Open Observe API

Integration with OpenObserve, an open-source observability platform for logs, metrics, and traces.

### Features

- Send logs to OpenObserve streams
- Basic authentication support
- Configurable default organization
- System Manager permissions
- Test connection functionality
- Available in safe_exec contexts (Server Scripts, Business Logic)

### Configuration

Navigate to **Open Observe API** in Frappe and configure:

1. **URL**: Your OpenObserve instance URL (e.g., `https://api.openobserve.ai`)
2. **User**: Username/email for authentication
3. **Password**: Password (stored securely)
4. **Default Organization**: Optional default organization name

### Usage

#### From Python

```python
import frappe

# Send logs
result = frappe.call(
    "tweaks.tweaks.doctype.open_observe_api.open_observe_api.send_logs",
    stream="my-stream",
    logs=[{"message": "Test log", "level": "info"}]
)
```

#### From Server Scripts

```python
# Available in safe_exec context
frappe.open_observe.send_logs(
    stream="my-stream",
    logs=[{"message": "Test log", "level": "info"}]
)
```

#### From JavaScript

```javascript
frappe.call({
    method: 'tweaks.tweaks.doctype.open_observe_api.open_observe_api.send_logs',
    args: {
        stream: 'my-stream',
        logs: [{message: 'Test log', level: 'info'}]
    }
});
```

### API

#### send_logs(stream, logs, org=None)

Send logs to an OpenObserve stream.

- **stream** (str): Stream name
- **logs** (list): List of log dictionaries
- **org** (str, optional): Organization name (uses default_org if not provided)

Returns dictionary with `success`, `response`, and `status_code`.

#### test_connection()

Test connection to OpenObserve API.

Returns dictionary with `success`, `message`, and optional `details` or `error`.

### Permissions

- Only **System Managers** can send logs
- Configuration requires System Manager role

### Documentation

- See [EXAMPLES.md](./EXAMPLES.md) for detailed usage examples
- See [.github/instructions/open-observe-api.instructions.md](../../../../.github/instructions/open-observe-api.instructions.md) for development guidelines
- OpenObserve API: https://openobserve.ai/docs/api/

### Testing

Run tests:
```bash
bench --site development.localhost run-tests --app tweaks --doctype "Open Observe API"
```

### License

MIT
