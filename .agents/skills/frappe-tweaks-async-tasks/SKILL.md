---
name: frappe-tweaks-async-tasks
description: Expert guidance for enqueueing and managing Async Tasks in Frappe Tweaks. Use when working with enqueue_async_task, enqueue_safe_async_task, Async Task Log, Async Task Type, implementing concurrency limits, per-method priority ordering, task cancellation, or choosing between Async Tasks and standard frappe.enqueue background jobs.
---

# Async Tasks Expert

Expert guidance for the Frappe Tweaks Async Task system — a managed, observable alternative to raw `frappe.enqueue`.

## When to Use Async Tasks vs `frappe.enqueue`

| Concern | `frappe.enqueue` | Async Tasks |
|---|---|---|
| Observability | No built-in log | Full log: status, timing, errors, memory |
| Concurrency control | None | Per-method `concurrency_limit` |
| Priority ordering | None | Per-method `priority` + per-task `at_front` |
| Cancellation | Cannot cancel | Cancel from UI or code |
| Server Script support | No | Yes (`call_whitelisted_function=True`) |
| Deduplication | Optional (`job_id`) | Via dispatcher deduplication |

**Use Async Tasks when any of the following apply:**
- You need to see task status, errors, or execution time in the UI
- Multiple agents/jobs can enqueue the same method and you need a cap on concurrency
- You want tasks to queue up and respect a priority order rather than flood workers
- The method is a whitelisted function or Server Script
- You need to be able to cancel tasks programmatically

**Stick with `frappe.enqueue` when:**
- The job is fire-and-forget with no UI visibility required
- You are inside a framework hook that already handles retries/logging (e.g., Sync Jobs)

## Public API

```python
from tweaks.tweaks.doctype.async_task_log.async_task_log import (
    enqueue_async_task,
    enqueue_safe_async_task,
)
```

### `enqueue_async_task`

```python
task = enqueue_async_task(
    method,                         # dotted path str OR callable
    queue="default",                # "default" | "short" | "long"
    timeout=300,                    # seconds; default 300
    at_front=False,                 # jump ahead of other Pending tasks for this method
    call_whitelisted_function=False,# execute via call_whitelisted_function (Server Scripts)
    **kwargs,                       # forwarded to method as keyword arguments
)
# task.name  → Async Task Log document name
```

### `enqueue_safe_async_task`

Shorthand for `enqueue_async_task(..., call_whitelisted_function=True)`. Use when calling whitelisted functions or Server Scripts by name.

```python
task = enqueue_safe_async_task(
    "myapp.api.sync_customer",
    queue="short",
    customer_id="CUST-0001",
)
```

### Passing a Callable

```python
from myapp.utils import process_invoice

task = enqueue_async_task(process_invoice, invoice_name="INV-001")
# Internally resolves to "myapp.utils.process_invoice"
```

## Async Task Type (optional configuration)

Create an **Async Task Type** document with `method` matching the dotted path to configure:

| Field | Default | Effect |
|---|---|---|
| `priority` | 0 | Higher = dispatched first among Pending tasks |
| `concurrency_limit` | 0 (unlimited) | Max simultaneous Queued/Started tasks for this method |
| `is_standard` | False | Protect from accidental deletion in production |

**Creating via code (fixtures/patches):**

```python
frappe.get_doc({
    "doctype": "Async Task Type",
    "method": "myapp.utils.heavy_import",
    "priority": 10,
    "concurrency_limit": 2,
    "is_standard": 1,
}).insert(ignore_if_duplicate=True)
```

## Status Lifecycle

```
Pending → Queued → Started → Finished
                           ↘ Failed
          ↘ Canceled  (from Pending, Queued, or Started)
```

- **Pending**: Created, waiting for dispatcher to promote it.
- **Queued**: Pushed to RQ, waiting for a worker.
- **Started**: Worker picked it up.
- **Finished / Failed**: Terminal states. `error_message` populated on failure.
- **Canceled**: Manually canceled; RQ job stopped if already Queued/Started.

A realtime event `async_task_status` is published to the creating user on **every status transition** (Queued, Started, Finished, Failed, Canceled). Listen for this event to react to any stage, not just completion.

```python
# Payload: {"name": task_name, "status": new_status, "message": optional_message}
frappe.realtime.on("async_task_status", (data) => { ... })
```

You can also push a custom message alongside a status update by calling `notify_status()` directly:

```python
task.notify_status(message="Processing row 42 of 100...")
```

To send a progress notification **from inside the executing method** (where you don't have the task document), use the `notify_task_status` utility:

```python
from tweaks.tweaks.doctype.async_task_log.async_task_log import notify_task_status

def my_long_running_job(items):
    for i, item in enumerate(items):
        process(item)
        notify_task_status(message=f"Processed {i + 1} of {len(items)}")
```

`notify_task_status` resolves the current RQ job, looks up the matching `Async Task Log`, and calls `notify_status()` on it. It is a no-op when called outside a worker context.

## Cancellation

```python
task = frappe.get_doc("Async Task Log", task_name)
task.cancel()  # works from Pending, Queued, or Started
```

## Observability

Each `Async Task Log` document stores:
- `started_at`, `ended_at`, `time_taken`
- `peak_memory_usage` (RSS, KB)
- `error_message` with full traceback on failure
- `debug_log` if `frappe.debug_log` is populated
- `job_id` linking to the underlying RQ Job

## Dispatch & Recovery

Tasks are never dropped. The dispatcher runs:
1. After every new task insert (`after_insert` hook)
2. After every task completes (success or failure)
3. Via the scheduler (`all` event) as a recovery mechanism for missed triggers

See [references/implementation.md](references/implementation.md) for the full dispatch algorithm and concurrency internals.
See [references/comparison_with_prepared_report.md](references/comparison_with_prepared_report.md) for a side-by-side schema and implementation comparison with Frappe's built-in Prepared Report.

## Source Code

- `tweaks/tweaks/doctype/async_task_log/async_task_log.py` — Public API + Document controller
- `tweaks/tweaks/doctype/async_task_log/async_task_log_dispatch.py` — Dispatch algorithm
- `tweaks/tweaks/doctype/async_task_type/async_task_type.py` — Type configuration
