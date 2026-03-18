---
name: frappe-tweaks-async-tasks
description: Expert guidance for enqueueing and managing Async Tasks in Frappe Tweaks. Use when working with enqueue_async_task, enqueue_safe_async_task, bulk_enqueue_async_task, bulk_enqueue_safe_async_task, toggle_dispatcher, Async Task Log, Async Task Type, implementing concurrency limits, per-method priority ordering, task cancellation, batch/bulk task submission, document action tasks (document_type/document_name/document_action), dispatcher control, auto-retry on failure (max_retries, retry_delay, retry_count), or choosing between Async Tasks and standard frappe.enqueue background jobs.
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
| Auto-retry on failure | No | Yes (`max_retries` + `retry_delay`) |

**Use Async Tasks when any of the following apply:**
- You need to see task status, errors, or execution time in the UI
- Multiple agents/jobs can enqueue the same method and you need a cap on concurrency
- You want tasks to queue up and respect a priority order rather than flood workers
- The method is a whitelisted function or Server Script
- You need to be able to cancel tasks programmatically
- You want failed tasks to be automatically retried after a configurable delay

**Stick with `frappe.enqueue` when:**
- The job is fire-and-forget with no UI visibility required
- You are inside a framework hook that already handles retries/logging (e.g., Sync Jobs)

## Public API

```python
from tweaks.tweaks.doctype.async_task_log.async_task_log import (
    enqueue_async_task,
    enqueue_safe_async_task,
    bulk_enqueue_async_task,
    bulk_enqueue_safe_async_task,
)
from tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch import (
    toggle_dispatcher,
    can_dispatch_now,
)
```

### `enqueue_async_task`

```python
task = enqueue_async_task(
    method=None,                    # dotted path str OR callable; optional when document_* fields are set
    queue="default",                # "default" | "short" | "long"
    timeout=300,                    # seconds; default 300
    job_name=None,                  # human-readable label (title); defaults to method when omitted
    # --- document action shorthand (alternative to method) ---
    document_type=None,             # DocType name  ┐ all three must be provided
    document_name=None,             # document name ┤ together; method is then auto-derived
    document_action=None,           # method to call on the document (e.g. "submit") ┘
    # --- retry options ---
    max_retries=0,                  # max automatic retry attempts on failure; 0 = no retries
    retry_delay=None,               # seconds to wait after failure before retrying; None = retry immediately
    # --- other options ---
    at_front=False,                 # jump ahead of other Pending tasks for this method
    call_whitelisted_function=False,# execute via call_whitelisted_function (Server Scripts)
    batch_id=None,                  # optional batch group label; tasks sharing a batch_id are ordered together
    batch_order=None,               # position within the batch; lower values dispatch first
    arguments=None,                 # explicit dict of method kwargs; overrides **kwargs on key collision
    **kwargs,                       # forwarded to method / document action as keyword arguments
)
# task.name  → Async Task Log document name
```

**Rules:**
- Pass either `method` **or** all three of `document_type` + `document_name` + `document_action`. Passing neither raises `ValueError`.
- When the document fields are used, `method` is automatically derived as the doctype controller dotted path + `".{action}"` (e.g. `"erpnext.accounts.doctype.sales_invoice.sales_invoice.submit"`).
- `job_name` is an optional human-readable label stored as the task title. When omitted, it is set to `method` automatically in `before_insert`.
- Inner function resolution is applied at execution time: if the document controller defines `_submit`, it is called instead of `submit` (mirroring `Document.queue_action`).
- Use `arguments={"queue": "short"}` (not `queue=` in `**kwargs`) whenever a method argument name collides with an `enqueue_async_task` API parameter — `arguments` takes priority over `**kwargs` and its keys are never intercepted by the function signature.
- `max_retries=0` (the default) disables automatic retries. Set to a positive integer to enable them.
- `retry_delay` is the number of seconds to wait (measured from the task's `modified` timestamp on failure) before the next retry attempt. `None` or `0` means retry on the next dispatch cycle.

### `enqueue_safe_async_task`

Shorthand for `enqueue_async_task(..., call_whitelisted_function=True)`. Use when calling whitelisted functions or Server Scripts by name. Accepts the same `job_name`, `max_retries` and `retry_delay` parameters.

```python
task = enqueue_safe_async_task(
    "myapp.api.sync_customer",
    queue="short",
    customer_id="CUST-0001",
)
```

### `bulk_enqueue_async_task`

Create **multiple** `Async Task Log` documents in one call and dispatch them together as a single ordered batch.

```python
tasks = bulk_enqueue_async_task(
    tasks=[                             # list of per-task dicts (same keys as enqueue_async_task)
        {"method": "myapp.utils.process_invoice", "invoice_name": "INV-001"},
        {"method": "myapp.utils.process_invoice", "invoice_name": "INV-002", "at_front": True},
    ],
    batch_id="my-import-run-abc",       # optional; auto-generated uuid4 when omitted
    queue="short",                      # kwargs here overwrite matching keys in every task dict
)
```

**How it works:**

1. If `batch_id` is not given, a random UUID is assigned so all tasks share the same batch.
2. Each task's `batch_order` is set sequentially (0, 1, 2 …) in insertion order.
3. The dispatcher is internally suspended while inserting to prevent partial dispatches, then resumed atomically once all documents are committed.
4. A single `dispatch_async_tasks` job is enqueued at the end, respecting concurrency limits for all inserted tasks.

**Key behaviour:**
- Extra `**kwargs` are merged into **every** task dict (useful for shared fields like `queue` or `timeout`).
- Individual task dicts can still override merged values before calling `enqueue_async_task`.
- Returns the `batch_id` string (auto-generated if not provided); use it to query `Async Task Log` by `batch_id` to track completion.

### `bulk_enqueue_safe_async_task`

Shorthand for `bulk_enqueue_async_task(..., call_whitelisted_function=True)`. Use when each method is a whitelisted function or Server Script name.

```python
bulk_enqueue_safe_async_task(
    tasks=[
        {"method": "myapp.api.sync_customer", "customer_id": "CUST-0001"},
        {"method": "myapp.api.sync_customer", "customer_id": "CUST-0002"},
    ],
    queue="short",
)
```

### Passing a Callable

```python
from myapp.utils import process_invoice

task = enqueue_async_task(process_invoice, invoice_name="INV-001")
# Internally resolves to "myapp.utils.process_invoice"
```

### Document Action Shorthand

Use `document_type` + `document_name` + `document_action` instead of `method` when you want to call a method on a specific document in the background. This is the async-task equivalent of `doc.queue_action()`.

```python
# Submit a Sales Invoice in the background
task = enqueue_async_task(
    document_type="Sales Invoice",
    document_name="SINV-0042",
    document_action="submit",
    queue="long",
)

# Call a custom document method with kwargs
task = enqueue_async_task(
    document_type="My Doctype",
    document_name="MY-001",
    document_action="my_custom_method",
    some_arg="value",
)
```

**Execution behaviour:**
1. `frappe.get_doc(document_type, document_name)` is called inside the worker.
2. `doc.unlock()` is called to release any file lock left from the caller.
3. Inner function resolution: if `doc._submit` exists and `document_action="submit"`, `_submit` is called instead.
4. `getattr(doc, action)(**kwargs)` is invoked with any extra kwargs.

**`Async Task Type` concurrency** is keyed on the derived `method` string, so you can set `concurrency_limit` on `"erpnext.accounts.doctype.sales_invoice.sales_invoice.submit"` as usual.

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
                           ↘ Failed ──(auto-retry)──→ Pending
          ↘ Canceled  (from Pending, Queued, or Started)
```

- **Pending**: Created, waiting for dispatcher to promote it.
- **Queued**: Pushed to RQ, waiting for a worker.
- **Started**: Worker picked it up.
- **Finished / Failed**: Terminal states. `error_message` populated on failure.
- **Canceled**: Manually canceled; RQ job stopped if already Queued/Started.
- **Auto-retry**: When a task has `max_retries > 0` and `retry_count < max_retries`, the dispatcher automatically resets it to `Pending` after the `retry_delay` has elapsed since the last failure. `retry_count` is incremented each time a retry is triggered.

A realtime event `async_task_status` is published to the creating user on **every status transition** (Queued, Started, Finished, Failed, Canceled). Use `frappe.async_tasks.show_progress` (see [JavaScript API](#javascript-api) below) for the idiomatic high-level approach. For raw access:

```javascript
// Payload: { name, status, message, error }
// Always filter by name — events are broadcast for ALL tasks
frappe.realtime.on("async_task_status", ({ name, status, message, error }) => { ... })
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

## JavaScript API

A thin JS namespace `frappe.async_tasks` is available on every desk page, provided by `tweaks/public/js/tweaks/async_tasks.js`.

### `frappe.async_tasks.show_progress(name, title?, handler?)`

High-level wrapper around `frappe.realtime.on("async_task_status", …)` that drives a `frappe.show_progress` bar for a given task. Use this instead of wiring the raw realtime event by hand.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | Yes | `Async Task Log` document name to track. |
| `title` | `string` | No | Progress bar title. Defaults to `"Task {name}"`. |
| `handler` | `function` | No | Optional callback invoked on every status event: `({ name, status, message, error }) => void`. |

**Behaviour:**
- Immediately shows the progress bar at 10 % ("Pending").
- Registers the `async_task_status` realtime listener **before** fetching current status, so no transition event is missed.
- Fetches the task's current status via `frappe.client.get_value`. If the task is already in a terminal state, the handler fires immediately without waiting for a realtime event.
- On **Failed**, calls `frappe.throw(error)` to surface the error message in a dialog.
- The realtime listener is automatically deregistered once a terminal status (`Finished`, `Failed`, `Canceled`) is received.

```javascript
// Enqueue via a server call, then track progress
frappe.call({
    method: "myapp.api.start_import",
    callback(r) {
        frappe.async_tasks.show_progress(
            r.message,              // Async Task Log name
            __("Importing data"),   // progress bar title
            ({ status }) => {
                if (status === "Finished") frappe.show_alert(__("Import complete!"))
            }
        )
    },
})
```

## Cancellation

```python
task = frappe.get_doc("Async Task Log", task_name)
task.cancel()  # works from Pending, Queued, or Started
```

## Retry

Failed tasks can be retried manually or automatically.

### Manual retry

```python
task = frappe.get_doc("Async Task Log", task_name)
task.retry()        # reset to Pending and trigger dispatch
task.retry(now=True)  # enqueue for immediate execution (skip dispatcher)
```

`retry()` raises if called on a non-Failed/non-Canceled task.

### Automatic retry

Set `max_retries` (and optionally `retry_delay`) when creating the task:

```python
task = enqueue_async_task(
    "myapp.utils.sync_customer",
    max_retries=3,
    retry_delay=60,   # wait 60 seconds after failure before retrying
    customer_id="CUST-001",
)
```

The dispatcher calls `retry_failed_tasks()` at the start of every dispatch pass. It queries all `Failed` tasks where `max_retries > 0` and `retry_count < max_retries`, then resets those whose `retry_delay` has elapsed since their `modified` timestamp. Each retry increments `retry_count`. When `retry_count` reaches `max_retries` the task stays `Failed` and is no longer picked up automatically.

**Key points:**
- `retry_count` tracks how many automatic (or manual) retries have been triggered, not how many failures occurred.
- `retry_delay=None` (or `0`) means retry on the very next dispatch cycle.
- Per-task errors in `retry_failed_tasks` are logged and do not block retries of other tasks.

## Observability

Each `Async Task Log` document stores:
- `job_name` — human-readable label used as the document title (defaults to `method`)
- `started_at`, `ended_at`, `time_taken`
- `peak_memory_usage` (RSS, KB)
- `error_message` with full traceback on failure
- `debug_log` if `frappe.debug_log` is populated
- `job_id` linking to the underlying RQ Job
- `document_type`, `document_name`, `document_action` — persisted when created via the document action shorthand; used at execution time to re-fetch the document and call the action
- `max_retries`, `retry_delay`, `retry_count` — retry configuration and current retry counter

## Dispatcher Control

The dispatcher can be suspended site-wide, which prevents any new tasks from being promoted to `Queued`. Already-`Queued` workers continue running.

### `toggle_dispatcher` (whitelisted)

Requires **System Manager** role. Persists the suspended/running state as a site default so it survives process restarts.

```python
from tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch import toggle_dispatcher

toggle_dispatcher(enable=False)  # suspend — no new tasks will be dispatched
toggle_dispatcher(enable=True)   # resume  — dispatcher runs normally again
```

Can also be called via the HTTP API (it is `@frappe.whitelist()`):

```
POST /api/method/tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch.toggle_dispatcher
{ "enable": 1 }   // or 0
```

### `can_dispatch_now`

Returns `True` when the dispatcher is running (not suspended). Use this guard before triggering dispatch manually:

```python
from tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch import can_dispatch_now

if can_dispatch_now():
    enqueue_dispatch_async_tasks()
```

> **Note:** `bulk_enqueue_async_task` internally suspends the dispatcher while inserting tasks and calls `_set_dispatcher_state` directly (bypassing the `System Manager` permission check that wraps the public `toggle_dispatcher`). Never call `toggle_dispatcher` from inside a background worker for internal use — use `_set_dispatcher_state` instead.

## Dispatch & Recovery

Tasks are never dropped. The dispatcher runs:
1. After every new task insert (`after_insert` hook)
2. After every task completes (success or failure)
3. Via the scheduler (`all` event) as a recovery mechanism for missed triggers

See [references/implementation.md](references/implementation.md) for the full dispatch algorithm and concurrency internals.
See [references/comparison_with_prepared_report.md](references/comparison_with_prepared_report.md) for a side-by-side schema and implementation comparison with Frappe's built-in Prepared Report.
See [references/comparison_with_rq_job.md](references/comparison_with_rq_job.md) for a side-by-side schema and lifecycle comparison with Frappe's built-in RQ Job virtual DocType.
See [references/comparison_with_scheduled_job.md](references/comparison_with_scheduled_job.md) for a side-by-side schema and implementation comparison with Frappe's Scheduled Job Type / Scheduled Job Log.

## Source Code

- `tweaks/tweaks/doctype/async_task_log/async_task_log.py` — Public API + Document controller
- `tweaks/tweaks/doctype/async_task_log/async_task_log_dispatch.py` — Dispatch algorithm
- `tweaks/tweaks/doctype/async_task_type/async_task_type.py` — Type configuration
