# Async Task vs Scheduled Job Type / Scheduled Job Log

## Purpose

| | Async Task + Async Task Type | Scheduled Job Type + Scheduled Job Log |
|---|---|---|
| **Core role** | On-demand, deferred execution of arbitrary Python callables with concurrency control | Time-driven, recurring execution of registered Python hooks |
| **Trigger** | Explicitly created via `enqueue_async_task()` or by inserting an `Async Task` document | Triggered automatically by the Frappe scheduler process at the configured interval/cron |
| **Recurrence** | One-shot; each document = one execution | Repeating; one `Scheduled Job Type` record fires indefinitely |
| **Who defines the work** | Caller at runtime (any method + any kwargs) | Framework/app developer at install time via `hooks.py` or the UI |

---

## Schema Comparison

### Async Task Type vs Scheduled Job Type

| Field | Async Task Type | Scheduled Job Type |
|---|---|---|
| `method` | ✅ Data, unique, named by fieldname | ✅ Data, read-only, named by last two dotted segments |
| `priority` | ✅ Int — higher = dispatched first | ❌ no concept |
| `concurrency_limit` | ✅ Int — max simultaneous tasks for this method | ❌ no concept |
| `is_standard` | ✅ Check | ❌ |
| `frequency` | ❌ | ✅ Select (All / Hourly / Daily / Weekly / Monthly / Cron / …) |
| `cron_format` | ❌ | ✅ Data — only shown when `frequency = Cron` |
| `stopped` | ❌ | ✅ Check — disables execution without deleting the record |
| `create_log` | ❌ | ✅ Check — whether to create a `Scheduled Job Log` entry |
| `last_execution` | ❌ | ✅ Datetime |
| `next_execution` | ❌ | ✅ Datetime (virtual, computed from cron) |
| `server_script` | ❌ | ✅ Link — alternative to a Python method |
| `scheduler_event` | ❌ | ✅ Link |
| **Autoname** | `field:method` | `.join(method.split('.')[-2:])` |
| **track_changes** | ✅ | ✅ |

### Async Task vs Scheduled Job Log

| Field | Async Task | Scheduled Job Log |
|---|---|---|
| `status` | `Pending / Queued / Started / Finished / Failed / Canceled` | `Scheduled / Start / Complete / Failed` |
| `method` | ✅ Data (the callable path) | ❌ (looked up via `scheduled_job_type` link) |
| `scheduled_job_type` | ❌ | ✅ Link to `Scheduled Job Type` |
| `queue` | ✅ Select (default / short / long) | ❌ |
| `at_front` | ✅ Check | ❌ |
| `timeout` | ✅ Duration | ❌ |
| `job_id` | ✅ RQ job UUID | ❌ |
| `kwargs` | ✅ JSON — arbitrary arguments | ❌ (scheduled jobs take no runtime arguments) |
| `started_at` | ✅ Datetime | ❌ |
| `ended_at` | ✅ Datetime | ❌ |
| `time_taken` | ✅ Duration | ❌ |
| `peak_memory_usage` | ✅ Int (KB) | ❌ |
| `error_message` | ✅ Long Text | ❌ |
| `debug_log` | ✅ Code | ✅ Code |
| `details` | ❌ | ✅ Code (general execution details) |
| **Autoname** | `hash` | default (hash) |
| **Linked type record** | _(optional)_ via `Async Task Type` method match | ✅ required `scheduled_job_type` link |

---

## Implementation Comparison

### Execution trigger

**Scheduled Job Type** — driven by the Frappe scheduler polling loop. `ScheduledJobType.enqueue()` checks `is_event_due()` and calls `frappe.utils.background_jobs.enqueue()` with a fixed `rq_job_id` to prevent duplicates.

**Async Task** — trigger is explicit: a caller inserts an `Async Task` document. The `after_insert` hook calls `enqueue_dispatch_async_tasks()`, which runs the dispatcher in a worker. The scheduler also calls `dispatch_async_tasks()` on the `All` event as a recovery mechanism.

### Dispatch / queuing

**Scheduled Job Type** — simple: one event → one RQ job, deduplicated by a stable `rq_job_id` (`scheduled_job::<method>`). No concurrency control beyond that deduplication.

**Async Task** — multi-step dispatcher:
1. A `filelock` prevents concurrent dispatcher runs (exits immediately if locked).
2. Collects all distinct methods with `status = Pending`.
3. Loads `Async Task Type` configs in a single query to get `priority` and `concurrency_limit`.
4. Sorts methods by `priority DESC`.
5. For each method, counts active tasks (`Queued | Started`); promotes `Pending → Queued` up to `concurrency_limit` slots, ordering by `at_front DESC, creation ASC`.

### Status lifecycle

```
Scheduled Job Log:  (created as Scheduled) → Start → Complete / Failed

Async Task:  Pending → Queued → Started → Finished / Failed
                                         └───────────────→ Canceled (via cancel())
```

### Error handling

Both use `@dangerously_reconnect_on_connection_abort` for the error-saving function to survive DB connection drops.

**Scheduled Job Type** — calls `self.log_status("Failed")` which rolls back the DB transaction and writes a `Scheduled Job Log` entry.

**Async Task** — `_save_error(task, error)` reloads the document, sets `status = Failed`, and saves; called in the `except` handler of `execute_async_task`. The full traceback from `frappe.get_traceback(with_context=True)` is stored on `error_message`.

### Logging / observability

| Aspect | Async Task | Scheduled Job Type |
|---|---|---|
| Execution record | The `Async Task` document itself | Separate `Scheduled Job Log` child (linked) |
| `debug_log` capture | ✅ `frappe.debug_log` joined and stored | ✅ stored in log |
| `peak_memory_usage` | ✅ via `resource.getrusage` | ❌ |
| Timing fields | `started_at`, `ended_at`, `time_taken` | `last_execution` on the type record |
| Realtime event | `async_task_complete` broadcast | ❌ |

### Cancellation

**Scheduled Job Type** — `stopped` flag prevents future enqueuing; no in-flight cancellation.

**Async Task** — `cancel()` whitelisted method: stops an RQ job if `Started` (via `RQJob.stop_job()`), deletes it if `Queued`, then sets `status = Canceled`.

### Cleanup

Both implement `clear_old_logs(days=30)` to purge old records using `frappe.qb`.

---

## Summary

| Concern | Async Task | Scheduled Job |
|---|---|---|
| Trigger | Explicit at runtime | Time-based (cron/interval) |
| Recurrence | One-shot | Recurring |
| Runtime arguments | ✅ JSON kwargs | ❌ |
| Priority ordering | ✅ | ❌ |
| Concurrency limit | ✅ per-method | ❌ |
| Queue choice | ✅ | ✅ (via frequency → queue name) |
| Cancellable | ✅ | Only via `stopped` flag |
| Execution record | Self-contained document | Separate `Scheduled Job Log` |
| DB storage | MariaDB | MariaDB |
