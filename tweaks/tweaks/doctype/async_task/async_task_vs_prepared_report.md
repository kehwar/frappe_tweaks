# Async Task vs Prepared Report

## Purpose

| | Async Task + Async Task Type | Prepared Report |
|---|---|---|
| **Core role** | General-purpose deferred execution of any Python callable with priority/concurrency control | Deferred generation of a specific Frappe Report, with results cached as a compressed attachment |
| **Trigger** | `enqueue_async_task()` or direct document insert | `make_prepared_report()` whitelist API or Report UI |
| **Work defined by** | Caller at runtime — any dotted-path method + JSON kwargs | Report name and filter values |
| **Output** | Side-effects of the called method | Gzipped JSON result file attached to the document |
| **Reuse / deduplication** | None built-in | `get_completed_prepared_report()` finds existing completed report with same filters |

---

## Schema Comparison

### Side-by-side fields

| Field | Async Task | Prepared Report |
|---|---|---|
| `status` | `Pending / Queued / Started / Finished / Failed / Canceled` | `Queued / Started / Completed / Error` |
| `method` | ✅ Data — Python dotted path | ❌ |
| `report_name` | ❌ | ✅ Data (required), search-indexed |
| `queue` | ✅ Select (default / short / long) | ❌ (hardcoded `long`) |
| `at_front` | ✅ Check | ❌ |
| `timeout` | ✅ Duration | ❌ (per-report via `Report.timeout`, default 25 min) |
| `job_id` | ✅ Data | ✅ Data |
| `kwargs` | ✅ JSON — arbitrary arguments | ❌ |
| `filters` | ❌ | ✅ Small Text — JSON-serialised filter dict |
| `filter_values` | ❌ | ✅ HTML (virtual, for display) |
| `started_at` | ✅ Datetime | ❌ (tracked via `job_id` → RQ Job) |
| `ended_at` | ✅ Datetime | ❌ |
| `time_taken` | ✅ Duration | ❌ |
| `peak_memory_usage` | ✅ Int (KB) | ✅ Int |
| `error_message` | ✅ Long Text | ✅ Text |
| `debug_log` | ✅ Code | ❌ |
| `started_at` / `queued_at` | `started_at` stored on document | `queued_at` is virtual → `creation` |
| `queued_by` | ❌ (implicitly `owner`) | ✅ virtual → `owner` |
| `report_end_time` | ❌ (`ended_at` instead) | ✅ Datetime |
| **Autoname** | `hash` | `hash` |
| **Module** | Tweaks | Core |
| **is_virtual** | ❌ | ❌ (but `queued_by`, `queued_at`, `next_execution` are virtual fields) |

### Async Task Type (companion) vs Prepared Report

`Prepared Report` has no companion configuration doctype. `Async Task Type` is an optional companion that configures `priority` and `concurrency_limit` per method — there is no equivalent in `Prepared Report`.

---

## Implementation Comparison

### Enqueueing

**Prepared Report**
```python
# after_insert
timeout = frappe.get_value("Report", self.report_name, "timeout")
enqueue(generate_report, queue="long", prepared_report=self.name,
        timeout=timeout or REPORT_TIMEOUT, enqueue_after_commit=True)
```
- Always uses the `long` queue.
- Timeout comes from the `Report` record (default 25 min).
- Enqueued directly to RQ — no dispatcher layer.

**Async Task**
```python
# after_insert → enqueue_dispatch_async_tasks() → dispatch_async_tasks() (worker)
```
- Queue chosen per task (default / short / long).
- Timeout is stored on the document.
- Indrect two-step: a lightweight dispatcher job runs first, then promotes `Pending → Queued` tasks respecting `concurrency_limit`.

### `started_at` / `job_id` recording

Both use the same pattern — a `update_job_id()` function called at the very start of the worker function, committing before any user work runs:

```python
# Prepared Report
def update_job_id(prepared_report):
    job = get_current_job()
    frappe.db.set_value("Prepared Report", prepared_report,
        {"job_id": job and job.id, "status": "Started"})
    frappe.db.commit()

# Async Task (mirrors the above, adds started_at)
def update_job_id(task_name):
    job = get_current_job()
    frappe.db.set_value("Async Task", task_name,
        {"job_id": job and job.id, "status": "Started", "started_at": now()})
    frappe.db.commit()
```

### Error handling

Both use `@dangerously_reconnect_on_connection_abort` on `_save_error`:

```python
# Prepared Report
@dangerously_reconnect_on_connection_abort
def _save_error(instance, error):
    instance.reload()
    instance.status = "Error"    # ← "Error"
    instance.error_message = error
    instance.save(ignore_permissions=True)

# Async Task (identical structure)
@dangerously_reconnect_on_connection_abort
def _save_error(task, error):
    task.reload()
    task.status = "Failed"       # ← "Failed"
    task.error_message = error
    task.save(ignore_permissions=True)
```

### Stale task expiry

Both implement a `expire_stalled_*` function that expires jobs stuck in `Started` for longer than `FAILURE_THRESHOLD = 6 hours`:

```python
# Prepared Report
def expire_stalled_report():
    frappe.db.set_value("Prepared Report",
        {"status": "Started", "modified": ("<", add_to_date(now(), seconds=-FAILURE_THRESHOLD, ...))},
        {"status": "Failed", "error_message": ...})

# Async Task — same logic via expire_stalled_tasks()
```

### Output / result storage

**Prepared Report** — results are serialised to JSON, compressed (`gzip`), and stored as a `File` attachment on the document. Retrieved later via `get_prepared_data()`.

**Async Task** — no output storage. The callable is responsible for any side-effects or result storage. `debug_log` is captured from `frappe.debug_log` and stored on the document.

### Realtime broadcast

Both publish a realtime event after completion:

```python
# Prepared Report
frappe.publish_realtime("report_generated",
    {"report_name": instance.report_name, "name": instance.name},
    user=frappe.session.user)

# Async Task
frappe.publish_realtime("async_task_complete",
    {"name": task.name, "status": task.status},
    user=frappe.session.user)
```

### Cancellation

**Prepared Report** — `on_trash` stops or deletes the underlying RQ job when the document is deleted.

**Async Task** — explicit `cancel()` whitelist method sets `status = Canceled` without deleting the document. Also handles `Pending` tasks (no RQ job yet — simply marks canceled).

### Dispatch after completion

**Prepared Report** — no post-completion hook; relies on direct RQ enqueue from `after_insert`.

**Async Task** — `execute_async_task` calls `enqueue_dispatch_async_tasks()` after each task finishes, triggering the dispatcher to fill freed concurrency slots.

---

## Status Lifecycle

```
Prepared Report:  Queued → Started → Completed
                                   └──────────→ Error

Async Task:       Pending → Queued → Started → Finished
                                              └─────────→ Failed
                  ↑ any of these states can become → Canceled
```

---

## Summary

| Concern | Async Task | Prepared Report |
|---|---|---|
| Work type | Any Python callable | Frappe Report generation only |
| Output storage | None (side-effects) | Gzipped JSON attachment |
| Queue selection | Per-task (default/short/long) | Always `long` |
| Priority | ✅ via Async Task Type | ❌ |
| Concurrency limit | ✅ per-method | ❌ |
| Deduplication | ❌ | ✅ same filters → reuse completed report |
| Timing tracking | `started_at`, `ended_at`, `time_taken` | `report_end_time` only |
| Cancellation | ✅ `cancel()` method | Only on trash |
| Debug log | ✅ | ❌ |
| `_save_error` pattern | ✅ identical | ✅ (origin) |
| `update_job_id` pattern | ✅ identical | ✅ (origin) |
| Stale expiry | ✅ same threshold (6 h) | ✅ same threshold (6 h) |
