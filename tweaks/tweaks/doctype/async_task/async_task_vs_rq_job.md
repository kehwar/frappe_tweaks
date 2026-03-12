# Async Task vs RQ Job

## Purpose

| | Async Task | RQ Job |
|---|---|---|
| **Core role** | Frappe-managed, MariaDB-persisted task queue with priority and concurrency control | Virtual read-only view over Redis Queue (RQ) jobs — raw worker state |
| **Persistence** | MariaDB (`tabAsync Task`) | Redis only — no DB table. `is_virtual = 1` |
| **Lifecycle ownership** | Frappe manages the full lifecycle (Pending → Queued → Started → Finished / Failed / Canceled) | Mirrors the internal RQ state; Frappe observes but does not drive it |
| **Created by** | Application code via `enqueue_async_task()` | Any `frappe.enqueue()` call (including by Async Task itself) |
| **Queried from** | `frappe.get_doc("Async Task", name)` → MariaDB | `frappe.get_doc("RQ Job", job_id)` → `Job.fetch()` from Redis |

---

## Schema Comparison

| Field | Async Task | RQ Job |
|---|---|---|
| `name` / primary key | Hash (MariaDB row) | RQ `job.id` (Redis key) |
| `job_id` | ✅ Data — RQ job UUID stored after dispatch | ✅ Data — **IS** the name (`autoname: field:job_id`) |
| `queue` | ✅ Select (default / short / long) | ✅ Select (default / short / long) |
| `status` | `Pending / Queued / Started / Finished / Failed / Canceled` | `queued / started / finished / failed / deferred / scheduled / canceled` (lowercase, RQ-native) |
| `method` | ✅ Data — Python dotted path | ❌ |
| `job_name` | ❌ | ✅ Data — human-readable name derived from kwargs |
| `timeout` | ✅ Duration | ✅ Duration |
| `at_front` | ✅ Check | ❌ |
| `kwargs` / `arguments` | `kwargs` — JSON, stored in DB | `arguments` — Code, serialised from `job.kwargs` at read time |
| `started_at` | ✅ Datetime (DB) | ✅ Datetime (from Redis, UTC-converted) |
| `ended_at` | ✅ Datetime (DB) | ✅ Datetime (from Redis) |
| `time_taken` | ✅ Duration (DB) | ✅ Duration (computed live from Redis timestamps) |
| `error_message` / `exc_info` | `error_message` Long Text (DB) | `exc_info` Code (from Redis) |
| `debug_log` | ✅ Code (DB) | ❌ |
| `peak_memory_usage` | ✅ Int KB (DB) | ❌ |
| `started_at` | stored on document after execution | reflected live from Redis |
| **Creation** | `autoname = hash` — MariaDB-generated | `autoname = field:job_id` — RQ-generated UUID |
| **Writable** | ✅ standard DocType | ❌ `db_insert`/`db_update` are no-ops; `is_virtual = 1` |
| **Module** | Tweaks | Core |

### Extra states in RQ Job not present in Async Task

| RQ status | Meaning |
|---|---|
| `deferred` | Job waiting on a dependency job to finish |
| `scheduled` | Job enqueued to run at a future time |

These states have no equivalent in Async Task because Async Task does not use RQ's deferred/scheduled mechanisms — it manages its own `Pending` state in MariaDB.

---

## Implementation Comparison

### Storage layer

**RQ Job** — entirely virtual. `load_from_db()` overrides the standard Frappe DB load and calls `Job.fetch()` from Redis directly. `get_list()` iterates RQ registries (queued, started, failed, …) and serialises job objects on the fly. No MariaDB rows are touched.

**Async Task** — standard Frappe DocType. Every state transition is a `frappe.db.set_value()` call. The MariaDB row survives after the job finishes (for auditing), until `clear_old_logs()` removes it.

### Relationship

Every `Queued` or `Started` Async Task corresponds to exactly one RQ Job. The link is `AsyncTask.job_id = RQJob.job_id`. `Async Task` is the Frappe-level record; `RQ Job` is the Redis-level record for the same unit of work.

```
AsyncTask (MariaDB)  ──job_id──→  RQ Job (Redis)
status: Queued                    status: queued
status: Started                   status: started
status: Finished / Failed         status: finished / failed  (RQ auto-transitions)
```

### Permissions model

**RQ Job** — only `System Manager` can read; only `Administrator` can delete. No write permission (virtual). A `check_permissions` decorator verifies the caller owns the job's site.

**Async Task** — `System Manager` has full CRUD. Cancellation is a `@frappe.whitelist()` method on the document.

### Cancellation

**RQ Job**
```python
def stop_job(self):   # sends SIGTERM to the worker running this job
    send_stop_job_command(connection=get_redis_conn(), job_id=self.job_id)

def cancel(self):     # only valid while status == "queued"
    self.job.cancel()

def delete(self):     # removes from Redis entirely
    self.job.delete()
```

**Async Task** — `cancel()` delegates to `RQ Job` for the underlying worker signal/delete, then sets its own `status = Canceled` in MariaDB:
```python
def cancel(self):
    if self.job_id:
        job = frappe.get_doc("RQ Job", self.job_id)
        if self.status == "Started":
            job.stop_job()
        elif self.status == "Queued":
            job.delete()
    self.db_set({"status": "Canceled", "ended_at": now()}, ...)
```

### List / filtering

**RQ Job** — `get_list()` and `get_matching_job_ids()` iterate all RQ queues and registries in Redis, filtering by `queue` and `status`. Cannot filter by method name or custom fields.

**Async Task** — standard `frappe.get_all()` / `frappe.qb` against MariaDB. Supports all standard Frappe filter operators on any stored field.

### Observability

| Aspect | Async Task | RQ Job |
|---|---|---|
| Available after job ends | ✅ permanently (until pruned) | ✅ briefly (finished registry TTL) |
| `debug_log` | ✅ | ❌ |
| `peak_memory_usage` | ✅ | ❌ |
| Realtime event | `async_task_complete` | ❌ |
| Frappe reports / list view | ✅ full filter/sort on all fields | ✅ limited (Redis-backed, no SQL) |

---

## Status Lifecycle

```
RQ Job (Redis-native):
  queued → started → finished
                  └──────────→ failed
         → deferred
         → scheduled
         → canceled

Async Task (Frappe/MariaDB):
  Pending → Queued   ← corresponds to RQ "queued"
            Queued → Started  ← corresponds to RQ "started"
                     Started → Finished  ← corresponds to RQ "finished"
                             └──────────→ Failed  ← corresponds to RQ "failed"
  *(any state)* → Canceled  ← Frappe-level; may or may not have a live RQ job
```

---

## Summary

| Concern | Async Task | RQ Job |
|---|---|---|
| Storage | MariaDB | Redis |
| Persistence after finish | ✅ permanent (configurable TTL) | Limited (Redis TTL) |
| Writable | ✅ | ❌ (virtual) |
| Filterable by method | ✅ | ❌ |
| Concurrency / priority | ✅ via dispatcher + Async Task Type | ❌ |
| `debug_log` | ✅ | ❌ |
| `peak_memory_usage` | ✅ | ❌ |
| Deferred / scheduled jobs | ❌ | ✅ |
| Cancellation | ✅ `cancel()` (delegates to RQ Job) | ✅ `stop_job()` / `cancel()` / `delete()` |
| Who uses whom | Creates and wraps RQ Jobs | Exposes raw RQ state |
