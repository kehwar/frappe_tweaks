# Async Task Log vs Prepared Report — Schema & Implementation Comparison

Side-by-side reference for understanding how `Async Task Log` (Frappe Tweaks) compares to Frappe's built-in `Prepared Report`. Useful when deciding which system to use, or when porting logic from one to the other.

---

## DocType Schema

| Field | Async Task Log | Prepared Report |
|---|---|---|
| **Naming** | `autoname: hash` | `autoname: hash` |
| `method` / `report_name` | `method` (Data) — dotted Python path or Server Script name | `report_name` (Data) — Frappe Report docname |
| `status` | `Select`: Pending / Queued / Started / Finished / Failed / Canceled | `Select`: Queued / Started / Completed / Error |
| `queue` | `Select` (default / short / long) | hardcoded `"long"` in `after_insert` |
| `timeout` | `Duration` (stored, forwarded to RQ) | fetched live from `Report.timeout`; fallback 25 min |
| `at_front` | `Check` — promotes task ahead of same-method peers | — not supported |
| `job_id` | `Data` (set on Queued → maps to RQ Job) | `Data` (set after Started via `get_current_job()`) |
| `kwargs` | `JSON` — arbitrary keyword arguments for the method | `filters` (Small Text JSON) — report filters only |
| `call_whitelisted_function` | `Check` — routes through `call_whitelisted_function` | — |
| `started_at` | `Datetime` | — (only `creation` / `queued_at` virtual) |
| `ended_at` | `Datetime` | `report_end_time` (Datetime) |
| `time_taken` | `Duration` (computed: `ended_at − started_at`) | — not stored |
| `peak_memory_usage` | `Int` (RSS KB) | `Int` (RSS KB) — same field, same approach |
| `error_message` | `Code` (full traceback) | `Text` (full traceback) |
| `debug_log` | `Code` (from `frappe.debug_log`) | — not captured |
| `queued_by` / owner | `owner` (standard Frappe field) | `queued_by` (virtual property → `self.owner`) |
| `queued_at` | `creation` (standard Frappe field) | `queued_at` (virtual property → `self.creation`) |
| Result storage | — (method writes its own output) | gzip-compressed JSON attached as a File |

---

## Status Lifecycle

### Async Task Log

```
Pending → Queued → Started → Finished
                           ↘ Failed
          ↘ Canceled  (cancelable from any pre-terminal state)
```

- `Pending` is a dispatcher-managed waiting state before the task is pushed to RQ.
- `Queued` means the RQ job exists and is waiting for a worker.
- Cancellation is explicit and supported at every pre-terminal state.

### Prepared Report

```
Queued → Started → Completed
                 ↘ Error
```

- No `Pending` state — the RQ job is enqueued directly in `after_insert`.
- No cancellation support at the framework level (though `on_trash` calls `job.stop_job()` / `job.delete()`).

---

## Enqueueing Flow

### Async Task Log

```python
# 1. Public API call
task = enqueue_async_task(method, queue="default", **kwargs)

# 2. after_insert → enqueue_dispatch_async_tasks() (deduplicated RQ job)
# 3. dispatch_async_tasks() runs in worker:
#    - fetches all Pending tasks, applies concurrency + priority ordering
#    - promotes eligible tasks to Queued via enqueue_execution()
# 4. execute_task(task_name) runs in worker:
#    - task.execute() → updates status, runs method, handles errors
```

Key difference: there is an **intermediate dispatcher step** that applies concurrency limits and priority ordering before any task touches RQ. Multiple tasks for the same method are serialised through this gate.

### Prepared Report

```python
# 1. Caller creates PreparedReport document (or calls make_prepared_report())
# 2. before_insert sets status = "Queued"
# 3. after_insert calls frappe.enqueue(generate_report, ..., enqueue_after_commit=True)
# 4. generate_report() runs in worker:
#    - calls update_job_id() → sets job_id + status="Started" then db.commit()
#    - generates report result, writes gzip File attachment
#    - sets status = "Completed" / "Error", saves, publishes realtime
```

No dispatcher — every `PreparedReport` insert immediately submits one RQ job. Concurrency control is absent; many reports can run in parallel.

---

## Concurrency & Priority

| Concern | Async Task Log | Prepared Report |
|---|---|---|
| Per-method concurrency cap | Yes — via `Async Task Type.concurrency_limit` | No |
| Priority ordering | Yes — `Async Task Type.priority` + per-task `at_front` | No |
| Deduplication | Via dispatcher filelock + deduplicated dispatch job | No |

---

## Realtime Notifications

### Async Task Log

Event name: `async_task_status`

```python
# Payload on every status transition:
{"name": task_name, "status": new_status, "message": optional_progress_text}
```

`notify_status()` is called inside `update_status()` after **every** `db_set`, so the client receives an event on each of: Queued, Started, Finished, Failed, Canceled. An optional `message` string carries progress text (set by `notify_task_status()` from inside the worker).

### Prepared Report

Event name: `report_generated`

```python
# Payload on terminal state only (Completed or Error):
{"report_name": instance.report_name, "name": instance.name}
```

Only one event is published, at the very end of `generate_report()`. No in-progress notifications.

---

## Error Handling

Both systems use `@dangerously_reconnect_on_connection_abort` on their `_save_error` helpers to survive database connection drops mid-execution.

### Async Task Log

- `_save_error` calls `update_status("Failed")` which sets `error_message`, `ended_at`, `time_taken`, `peak_memory_usage`.
- After saving the error, `enqueue_dispatch_async_tasks()` is called to unblock the next batch.
- Stalled tasks (stuck in `Started` > 6 h) are periodically reaped by `expire_stalled_tasks()`.

### Prepared Report

- `_save_error` sets `status = "Error"` and `error_message`, then calls `instance.save()`.
- `report_end_time` and `peak_memory_usage` are set unconditionally **after** the try/except, so both are always recorded.
- No stalled-task reaper; stale `Started` records must be resolved manually.

---

## Old Log Cleanup

| | Async Task Log | Prepared Report |
|---|---|---|
| Retention | 90 days (default) | 30 days (default) |
| Schedule | `daily_long` scheduler event | `daily_long` scheduler event |
| Mechanism | `AsyncTaskLog.clear_old_logs(days=90)` | `PreparedReport.clear_old_logs(days=30)` — enqueues batch-delete jobs |

---

## Result / Output Handling

**Async Task Log** makes no assumptions about output format. The called method is responsible for persisting any results (e.g., updating a document, writing a File, setting a field). The log stores only status and diagnostic data.

**Prepared Report** owns the output contract: `generate_report_result()` is called internally, and the result is gzip-compressed and stored as a `.gz` File attachment on the `Prepared Report` document. Consumers call `get_prepared_data()` to decompress and retrieve the data.

---

## Cancellation

| | Async Task Log | Prepared Report |
|---|---|---|
| Cancel from code | `task.cancel()` | Not available |
| Cancel from UI | Yes (via Document actions) | Not available |
| Cancel on trash | Yes — `cancel_job()` called in `on_trash` | Partial — `on_trash` calls `job.stop_job()` / `job.delete()` but does not update status |
| Cancelable states | Pending, Queued, Started | — |
| Post-cancel status | `Canceled` | — |

---

## Choosing Between the Two

Use **Async Task Log** when:
- You need concurrency limits, priority ordering, or task cancellation.
- You want fine-grained realtime progress updates during execution.
- The background job is not a Frappe Script Report.
- You want a unified log of task history across multiple methods.

Use **Prepared Report** when:
- You are running an existing Frappe/ERPNext Script Report or Custom Report in the background.
- The built-in result storage (gzip File attachment) and `get_prepared_data()` API meet your needs.
- You need the standard "Run in Background" button behaviour in the Frappe report UI.

---

## Source Files

| Component | Path |
|---|---|
| Async Task Log controller | `tweaks/tweaks/doctype/async_task_log/async_task_log.py` |
| Async Task Log schema | `tweaks/tweaks/doctype/async_task_log/async_task_log.json` |
| Async Task dispatch | `tweaks/tweaks/doctype/async_task_log/async_task_log_dispatch.py` |
| Async Task Type | `tweaks/tweaks/doctype/async_task_type/async_task_type.py` |
| Prepared Report controller | `frappe/frappe/core/doctype/prepared_report/prepared_report.py` |
| Prepared Report schema | `frappe/frappe/core/doctype/prepared_report/prepared_report.json` |
