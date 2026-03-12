# Async Tasks — Implementation Reference

Detailed internals of the Frappe Tweaks Async Task system. Read this when debugging dispatch behaviour, implementing concurrency limits, or understanding the RQ job lifecycle.

## Architecture Overview

```
enqueue_async_task()
    └─ insert AsyncTaskLog (status=Pending)
        └─ after_insert hook
            └─ enqueue_dispatch_async_tasks()   ← enqueued in RQ (deduplicated)
                └─ dispatch_async_tasks()        ← runs in worker
                    └─ _run_dispatch()
                        ├─ filelock (non-blocking)
                        ├─ retry_failed_tasks()  ← auto-retry eligible Failed tasks
                        ├─ fetch all Pending tasks + their AsyncTaskType config
                        ├─ fetch active counts per method
                        └─ for each task:
                            ├─ check concurrency_limit
                            └─ _enqueue_task() → enqueue_execution()
                                └─ enqueue execute_task() in RQ
                                    └─ task.execute()  ← runs in worker
```

## Dispatch Algorithm (`_run_dispatch`)

### Ordering

Pending tasks are fetched and ordered before dispatch:

1. `at_front DESC` — tasks flagged `at_front=True` are promoted first
2. `priority DESC` — resolved from linked `Async Task Type` (default 0)
3. `creation ASC` — FIFO within same priority

### Concurrency Guard

Before each task is enqueued, the dispatcher checks the in-memory active count:

```python
active = active_counts.get(method, 0)   # Queued + Started count
limit  = task.concurrency_limit or 0    # 0 = unlimited

if limit > 0 and active >= limit:
    continue  # skip — method is at capacity

_enqueue_task(task)
active_counts[method] = active + 1      # optimistic increment
```

Active counts are fetched once at the start of dispatch and incremented in-memory as tasks are promoted. This avoids re-querying the database per task.

### Filelock Protection

```python
with filelock(_DISPATCH_LOCK, timeout=0):
    _run_dispatch()
```

`timeout=0` means: if another dispatcher is already running, exit immediately. This prevents duplicate enqueues when many tasks are created at the same time (e.g., bulk inserts).

### Dispatcher Recovery

The dispatcher is also registered as a scheduled job (`all` event). Even if an `after_insert` trigger is missed (e.g., during a migration or crash), the scheduler will re-trigger dispatch within the next cycle.

## Auto-Retry (`retry_failed_tasks`)

`retry_failed_tasks()` is called at the start of every `_run_dispatch()` pass (inside the filelock). It:

1. Queries all `Failed` tasks where `max_retries > 0` and `retry_count < max_retries`.
2. For each candidate, checks whether `retry_delay` seconds have elapsed since `modified` (the timestamp of the last failure). If not, skips the task.
3. Calls `task.retry()` on eligible tasks, which increments `retry_count` and resets the task to `Pending` so it is dispatched in the same pass.
4. Wraps each retry in a try/except: per-task failures are logged to the Error Log without interrupting the rest.

## Task Execution (`execute`)

```python
def execute(self):
    try:
        self.update_status("Started")   # persists job_id, started_at + notifies
        self._execute()
        frappe.db.commit()
        self.update_status("Finished")  # persists ended_at, time_taken, peak_memory_usage + notifies
    except Exception:
        frappe.db.rollback()
        _save_error(self, ...)           # persists Failed + traceback

    enqueue_dispatch_async_tasks()       # trigger next batch
```

Realtime notifications are no longer a separate `publish_realtime` call at the end of `execute()`. Instead, `update_status()` calls `notify_status()` after every `db_set`, so the UI receives an event on **each** status transition.

The `_save_error` function is decorated with `@dangerously_reconnect_on_connection_abort` to survive database connection drops during error persistence.

### `_execute` — Method Resolution

```python
def _execute(self):
    kwargs = json.loads(self.kwargs or "{}")
    if self.call_whitelisted_function:
        from frappe.utils.safe_exec import call_whitelisted_function
        call_whitelisted_function(self.method, **kwargs)
    else:
        method = frappe.get_attr(self.method)
        method(**kwargs)
```

- **Normal mode**: resolves `method` via `frappe.get_attr` (standard Python import)
- **Whitelisted mode**: passes `method` string to `call_whitelisted_function`, which handles both Python whitelisted functions and Server Scripts by name

## `update_status` Payload Matrix

| Status | Extra fields set |
|---|---|
| `Started` | `job_id`, `started_at` |
| `Finished` | `ended_at`, `time_taken`, `peak_memory_usage` |
| `Failed` | `error_message` (traceback), `ended_at`, `time_taken`, `peak_memory_usage` |
| `Canceled` | `ended_at`, `time_taken`, `peak_memory_usage` |
| Any | `debug_log` (if `frappe.debug_log` populated) |

All `db_set` calls use `commit=True` and `notify=True`. After each `db_set`, `update_status()` also calls `notify_status()`, which publishes a realtime `async_task_status` event:

```python
def notify_status(self, message=None):
    frappe.publish_realtime(
        "async_task_status",
        {"name": self.name, "status": self.status, "message": message},
        user=frappe.session.user,
    )
```

This means the event fires on every transition (Queued, Started, Finished, Failed, Canceled), not just terminal states. The optional `message` param can carry progress text when calling `notify_status()` directly.

## Stalled Task Cleanup

`expire_stalled_tasks()` is a scheduled function that marks tasks as `Failed` if they have been in `Started` status for more than 6 hours (`FAILURE_THRESHOLD = 6 * 60 * 60`). Intended as a safety net for workers that crash mid-execution.

## Old Log Cleanup

`AsyncTaskLog.clear_old_logs(days=90)` deletes task logs older than `days` days. Registered as a scheduled job (`daily_long` event).

## Cancellation Flow

```python
task.cancel()
# → calls cancel_job() which stops the RQ job (if Started) or deletes it (if Queued)
# → calls update_status("Canceled")
```

On trash, if the task is Pending/Queued/Started, `cancel_job()` is called automatically.

## Async Task Type — Fixture Pattern

For standard configurations shipped with an app, create them as fixtures:

```python
# myapp/fixtures/async_task_types.json  (or create via patch)
[
    {
        "doctype": "Async Task Type",
        "method": "myapp.utils.nightly_reconciliation",
        "priority": 5,
        "concurrency_limit": 1,
        "is_standard": 1
    }
]
```

`is_standard=1` prevents non-developer users from modifying or deleting the record in production.

## Worker-Side Utilities

### `notify_task_status(message)`

Public helper for sending progress notifications from inside the method being executed:

```python
from tweaks.tweaks.doctype.async_task_log.async_task_log import notify_task_status

notify_task_status(message="Step 2 of 5 complete")
```

Internally delegates to `get_current_task().notify_status(message=message)`. Safe to call (no-op) when not running inside a worker.

### `get_current_task()`

Returns the `Async Task Log` document for the currently executing RQ job, or `None` if called outside a worker:

```python
job = get_current_job()              # rq's current job
task = frappe.db.exists("Async Task Log", {"job_id": job.id})
return frappe.get_doc("Async Task Log", task) if task else None
```

Useful when the executing method needs to inspect task metadata (e.g., `task.name`, `task.kwargs`) or call `task.notify_status()` directly.

## Related References

See [comparison_with_prepared_report.md](comparison_with_prepared_report.md) for a side-by-side schema and implementation comparison with Frappe's built-in `Prepared Report` doctype.

---

## RQ Job Relationship

Each `Async Task Log` holds one `job_id` pointing to the underlying `RQ Job` document. The `execute_task` function (the actual RQ job payload) loads the task by name and calls `task.execute()`.

```python
def execute_task(task_name):
    task = frappe.get_doc("Async Task Log", task_name)
    task.unlock()   # release document lock before execution
    task.execute()
```

## Integration with `enqueue_after_commit`

Both `enqueue_dispatch_async_tasks()` and `enqueue_execution()` use `enqueue_after_commit=True`. This ensures the task document is fully committed to the database before the worker tries to load it, preventing race conditions between the web process and the worker.

## DocType Schema Summary

### Async Task Log

| Field | Type | Notes |
|---|---|---|
| `method` | Data | Required. Dotted Python path or whitelisted function name |
| `queue` | Select | `default` / `short` / `long` |
| `timeout` | Duration | Seconds; default 300 |
| `at_front` | Check | Priority flag for this specific task |
| `call_whitelisted_function` | Check | Use `call_whitelisted_function` at execution |
| `kwargs` | JSON | Keyword arguments serialised as JSON |
| `status` | Select | Pending / Queued / Started / Finished / Failed / Canceled |
| `job_id` | Data | RQ Job ID (set on Started) |
| `started_at` / `ended_at` | Datetime | |
| `time_taken` | Duration | |
| `peak_memory_usage` | Int | RSS in KB |
| `error_message` | Code | Traceback on failure |
| `debug_log` | Code | `frappe.debug_log` captured during execution |
| `max_retries` | Int | Max automatic retry attempts; `0` = disabled (default) |
| `retry_delay` | Duration | Seconds to wait after failure before retrying; `None`/`0` = immediate |
| `retry_count` | Int | System-managed; incremented each time `retry()` is called |

### Async Task Type

| Field | Type | Notes |
|---|---|---|
| `method` | Data | Unique; named document key |
| `priority` | Int | Higher = dispatched first |
| `concurrency_limit` | Int | 0 = unlimited |
| `is_standard` | Check | Locks record in production |
