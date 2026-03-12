# Async Task Log vs RQ Job — Schema Comparison

Side-by-side reference for understanding how `Async Task Log` (Frappe Tweaks) relates to Frappe's built-in `RQ Job` virtual DocType. `RQ Job` surfaces the raw Redis Queue entry; `Async Task Log` is the persistent, observable wrapper that sits above it.

---

## Storage & Nature

| Aspect | Async Task Log | RQ Job |
|---|---|---|
| **Storage** | MariaDB — persistent beyond worker lifetime | Redis — ephemeral; purged after job TTL |
| **DocType kind** | Regular DocType | Virtual DocType (reads from Redis via `rq`) |
| **Lifecycle scope** | Born before the RQ job exists (`Pending`); survives after it is removed from Redis | Exists only while the RQ job is alive in Redis |
| **Link between them** | `async_task_log.job_id` → `rq_job.job_id` | No reference back to `Async Task Log` |

---

## DocType Schema

| Field | Async Task Log | RQ Job |
|---|---|---|
| **Naming** | `autoname: hash` (random UUID) | `autoname: By fieldname` (`job_id`) |
| Method / callable | `method` (Data) — dotted Python path or Server Script name | `job_name` (Data) — raw callable string stored by RQ |
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

## Status Lifecycle

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

## Key Differences

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

## Relationship at Runtime

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
