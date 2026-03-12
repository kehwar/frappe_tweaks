# Async Task Log vs RQ Job — Comparison

`Async Task Log` (Frappe Tweaks) is the persistent, observable wrapper that sits above RQ. `RQ Job` is Frappe's virtual DocType that surfaces the raw Redis Queue entry. Consult this document to understand how the two records relate at runtime, or when choosing where to read execution state.

---

## 1. Purpose & Trigger Model

| Dimension | Async Task Log | RQ Job |
|---|---|---|
| **What it is** | Persistent MariaDB record wrapping an RQ job | Ephemeral Redis entry representing a queued execution |
| **Created by** | `enqueue_async_task()` | Promoted by the ATL dispatcher (or `frappe.enqueue()` directly) |
| **Lifecycle scope** | Born before the RQ job exists (`Pending`); persists after Redis removes it | Exists only while the RQ job is alive in Redis |
| **Primary use case** | Observable, cancellable, concurrency-controlled background work | Raw task execution entry for RQ workers |

---

## 2. DocType Roles

| Role | Async Task system | RQ Job |
|---|---|---|
| **Execution record** | `Async Task Log` (MariaDB, permanent) | `RQ Job` (virtual DocType, reads from Redis) |
| **Configuration** | `Async Task Type` (optional) | — |
| **Link between them** | `async_task_log.job_id` → `rq_job.job_id` | No back-reference to `Async Task Log` |

---

## 3. Schema

| Field | Async Task Log | RQ Job |
|---|---|---|
| **Naming** | `autoname: hash` (random UUID) | `autoname: By fieldname` (`job_id`) |
| Method / callable | `method` (Data, optional when document fields are set) — dotted Python path or Server Script name | `job_name` (Data) — raw callable string stored by RQ |
| Document action | `document_type` (Link), `document_name` (DynamicLink), `document_action` (Data) — stored fields for the document action shorthand; execution fetches the doc and calls the action in the worker | — not supported |
| Status | `Select`: **Pending / Queued / Started / Finished / Failed / Canceled** (Title Case) | `Select`: **queued / started / finished / failed / deferred / scheduled / canceled** (lowercase) |
| Queue | `queue` (Select: default / short / long) | `queue` (Select: default / short / long) |
| Timeout | `timeout` (Duration) — stored at enqueue time | `timeout` (Duration) — read from RQ job |
| Job ID | `job_id` (Data) — set when promoted to Queued | `job_id` (Data, unique) — primary key of the virtual DocType |
| Arguments / kwargs | `kwargs` (JSON) — structured keyword arguments | `arguments` (Code) — raw string representation |
| Started at | `started_at` (Datetime) | `started_at` (Datetime) |
| Ended at | `ended_at` (Datetime) | `ended_at` (Datetime) |
| Time taken | `time_taken` (Duration) — computed: `ended_at − started_at` | `time_taken` (Duration) — computed by RQ |
| Error / exception | `error_message` (Code) — full traceback | `exc_info` (Code) — raw RQ exception string |
| Memory usage | `peak_memory_usage` (Int, RSS KB) | — not captured |
| Debug log | `debug_log` (Code) — `frappe.debug_log` output | — not captured |
| Priority / ordering | `at_front` (Check) — promotes task ahead of peers | — not supported |
| Whitelisted dispatch | `call_whitelisted_function` (Check) | — not applicable |
| Owner | `owner` (standard Frappe field — the enqueueing user) | — not stored |

---

## 4. Status Lifecycle

### Async Task Log

```
Pending → Queued → Started → Finished
                           ↘ Failed
          ↘ Canceled  (cancelable from Pending, Queued, or Started)
```

- **Pending**: Managed by the ATL dispatcher — task created but not yet pushed to RQ (e.g., blocked by `concurrency_limit`).
- **Queued**: RQ job created; `job_id` populated. Worker has not picked it up yet.
- **Started / Finished / Failed**: Mirror the underlying RQ job states.
- **Canceled**: ATL-level cancellation; RQ job is stopped if it was already Queued/Started.

### RQ Job

```
queued → started → finished
                 ↘ failed
queued → deferred
queued → scheduled
       → canceled
```

- **deferred**: Job postponed because a dependency hasn't finished.
- **scheduled**: Job is set to run at a future time.
- No equivalent of `Pending` — RQ only knows about jobs that have been pushed.

---

## 5. Execution Flow

```
enqueue_async_task(method, **kwargs)
        │
        ▼
 Async Task Log  [status=Pending, job_id=None]
        │  (dispatcher promotes when concurrency allows)
        ▼
 frappe.enqueue(method, job_id=..., **kwargs)
        │
        ▼
  RQ Job in Redis  [job_id links back to Async Task Log]
        │  (worker executes)
        ▼
 Async Task Log  [status=Finished|Failed, timing + memory recorded]
```

The `Async Task Log` owns the full lifecycle record. The `RQ Job` is the transient execution entry in Redis that the ATL promotes to and monitors.

---

## 6. Key Differences

| Concern | Async Task Log | RQ Job |
|---|---|---|
| **Persistence** | Permanent MariaDB record | Expires from Redis (default ~500 jobs retained) |
| **Pre-queue waiting** | `Pending` state with concurrency-aware dispatcher | Not supported — jobs go to Redis immediately |
| **Concurrency control** | `Async Task Type.concurrency_limit` per method | None — all queued jobs compete equally |
| **Priority ordering** | `Async Task Type.priority` + per-task `at_front` | FIFO within queue tier |
| **Observability** | Full: timing, memory, debug log, error, realtime events | Limited: timing, exception string |
| **Cancellation** | Supported via `task.cancel()` from any pre-terminal state | Supported via `frappe.utils.background_jobs.stop_job()` |
| **Server Script support** | Yes (`call_whitelisted_function=True`) | No |
| **Status vocabulary** | Title Case (`Finished`, `Failed`) | Lowercase (`finished`, `failed`) |

---

## 7. Concurrency & Priority

| Concern | Async Task Log | RQ Job |
|---|---|---|
| **Per-method limit** | `Async Task Type.concurrency_limit` | None — all queued jobs compete equally |
| **Priority ordering** | `Async Task Type.priority` + per-task `at_front` | FIFO within queue tier |
| **Pre-queue waiting** | `Pending` state; tasks wait for a concurrency slot | Not supported — enqueued immediately to Redis |
| **Deduplication** | Dispatcher filelock prevents duplicate promotions | Optional `job_id` deduplication via `frappe.enqueue` |

---

## 8. Cancellation

| | Async Task Log | RQ Job |
|---|---|---|
| **Supported** | Yes | Yes |
| **From UI** | Yes (whitelist action on form) | No |
| **From code** | `task.cancel()` | `frappe.utils.background_jobs.stop_job(job_id)` |
| **Effect on worker** | `stop_job()` if Started; `delete()` if Queued | Sends SIGINT to worker |
| **Cancelable states** | Pending, Queued, Started | Any non-terminal state |
| **Post-cancel status** | `Canceled` | `canceled` (lowercase) |

---

## 9. Realtime Notifications

| | Async Task Log | RQ Job |
|---|---|---|
| **Event name** | `async_task_status` | — |
| **Payload** | `{name, status, message}` | — |
| **Frequency** | Every status transition | — |
| **Custom messages** | `task.notify_status(message=...)` or `notify_task_status(message=...)` | — |
| **Target** | User who enqueued the task | — |

RQ Jobs have no realtime notification system. Callers must poll `frappe.call("frappe.core.doctype.rq_job.rq_job.get_status", ...)` to check job state.

---

## 10. Error Handling

| | Async Task Log | RQ Job |
|---|---|---|
| **Error storage** | `error_message` (Code) — full Python traceback | `exc_info` (Code) — raw RQ exception string |
| **Memory & timing on failure** | Recorded in `_save_error` | Not captured |
| **Debug log on failure** | Captured in `debug_log` | Not captured |
| **DB rollback before save** | Yes (`frappe.db.rollback()`) | N/A (managed by RQ internals) |
| **Connection abort recovery** | `_save_error` decorated with `@dangerously_reconnect_on_connection_abort` | No special handling |
| **Stalled task reaper** | Yes — `expire_stalled_tasks()` after 6 h Started | No |

---

## 11. Log Cleanup

| | Async Task Log | RQ Job |
|---|---|---|
| **Retention** | 90 days (default) | ~500 most recent jobs (Redis TTL) |
| **Schedule** | `daily_long` scheduler event | Automatic Redis key expiry |
| **Mechanism** | `AsyncTaskLog.clear_old_logs(days=90)` | Managed by RQ / Redis configuration |

---

## 12. When to Choose Each

Use **Async Task** when:
- You need to see task status, errors, or execution time after the job has run.
- You need to cap concurrency per method or prioritize tasks.
- You need cancellation support from UI or code.
- The task is triggered by user action or application logic.
- You want realtime progress updates in the browser.
- You are calling a whitelisted function or Server Script.

Use **`frappe.enqueue` / RQ Job directly** when:
- Fire-and-forget with no need for post-execution inspection.
- Integrating with existing framework hooks that already manage their own lifecycle (e.g., Sync Jobs).
- You need to inspect the raw Redis queue state for low-level debugging.

---

## 13. Source Files

| Component | Path |
|---|---|
| Async Task Log controller | `tweaks/tweaks/doctype/async_task_log/async_task_log.py` |
| Async Task Log schema | `tweaks/tweaks/doctype/async_task_log/async_task_log.json` |
| Async Task dispatch | `tweaks/tweaks/doctype/async_task_log/async_task_log_dispatch.py` |
| Async Task Type | `tweaks/tweaks/doctype/async_task_type/async_task_type.py` |
| RQ Job virtual DocType | `frappe/frappe/core/doctype/rq_job/rq_job.py` |
| RQ Job schema | `frappe/frappe/core/doctype/rq_job/rq_job.json` |

