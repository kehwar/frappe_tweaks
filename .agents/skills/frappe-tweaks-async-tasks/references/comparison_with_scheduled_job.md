# Async Task (Tweaks) vs Scheduled Job (Frappe Core) — Comparison

This reference compares the Tweaks **Async Task** system (Async Task Log + Async Task Type) with
Frappe Core's **Scheduled Job** system (Scheduled Job Type + Scheduled Job Log).

---

## 1. Purpose & Trigger Model

| Dimension | Async Task | Scheduled Job |
|---|---|---|
| **Triggered by** | Application code (`enqueue_async_task`) | Time-based scheduler (cron/frequency) |
| **Who initiates** | Any code path, agent, or user action | Frappe scheduler process automatically |
| **Repetition** | One-shot (enqueue once, runs once) | Recurring on a fixed schedule |
| **Primary use case** | On-demand background work with visibility | Periodic maintenance, sync, housekeeping |

---

## 2. DocType Roles

| Role | Async Task system | Scheduled Job system |
|---|---|---|
| **Configuration** | `Async Task Type` (optional, per method) | `Scheduled Job Type` (required, defines schedule) |
| **Execution log** | `Async Task Log` | `Scheduled Job Log` |
| **Naming** | `Async Task Log` — `autoname: hash` | `Scheduled Job Type` — `.`.join of last 2 method parts; `Scheduled Job Log` — autoname hash |

---

## 3. Schema: Configuration DocType

### Async Task Type

| Field | Type | Purpose |
|---|---|---|
| `method` | Data (unique, name field) | Dotted path to the Python callable |
| `priority` | Int (default 0) | Higher = dispatched first among Pending tasks |
| `concurrency_limit` | Int (default 0 = unlimited) | Max simultaneous Queued+Started tasks for this method |
| `is_standard` | Check | Protects record from accidental deletion |

**Optional**: creating an Async Task Type is not required. Tasks without a type record run with
default priority (0) and no concurrency limit.

### Scheduled Job Type

| Field | Type | Purpose |
|---|---|---|
| `method` | Data | Dotted path to the Python callable |
| `frequency` | Select | Cron frequency: All / Hourly / Daily / Weekly / Monthly / Cron / Yearly |
| `cron_format` | Data | Raw cron expression (only for `Cron` frequency) |
| `stopped` | Check | Pause execution without deleting the record |
| `create_log` | Check | Whether to create a `Scheduled Job Log`; forced on for non-`All` frequencies |
| `last_execution` | Datetime | Updated each run, used to calculate `next_execution` |
| `server_script` | Link → Server Script | Execute a Server Script instead of a Python method |
| `scheduler_event` | Link → Scheduler Event | Link to the event that registered this job |

**Required**: every scheduled job must have a `Scheduled Job Type` document. There is no equivalent
of "run without configuration".

---

## 4. Schema: Log DocType

### Async Task Log

| Field | Type | Notes |
|---|---|---|
| `method` | Data | Python dotted path |
| `queue` | Select (`default` / `short` / `long`) | RQ queue |
| `timeout` | Duration | Job timeout (seconds) |
| `at_front` | Check | Jump ahead of other Pending tasks for same method |
| `call_whitelisted_function` | Check | Execute via `call_whitelisted_function` instead of direct import |
| `kwargs` | JSON | Arguments forwarded to the method |
| `status` | Select | `Pending` / `Queued` / `Started` / `Finished` / `Failed` / `Canceled` |
| `job_id` | Data | RQ job ID (set when Queued) |
| `started_at` | Datetime | Worker start time |
| `ended_at` | Datetime | Worker end time |
| `time_taken` | Duration | Computed from `started_at` → `ended_at` |
| `peak_memory_usage` | Int | RSS in KB at task completion |
| `error_message` | Code / LongText | Full traceback on failure |
| `debug_log` | Code | `frappe.debug_log` captured during execution |

### Scheduled Job Log

| Field | Type | Notes |
|---|---|---|
| `scheduled_job_type` | Link → Scheduled Job Type | Parent job definition |
| `status` | Select | `Scheduled` / `Start` / `Complete` / `Failed` |
| `details` | Code | Traceback on failure |
| `debug_log` | Code | `frappe.debug_log` captured during execution |

**Key differences in log schema:**
- Async Task Log stores all execution parameters (`queue`, `timeout`, `kwargs`) — the log is
  self-contained and can be re-inspected without consulting a configuration document.
- Async Task Log records wall-clock timing (`started_at`, `ended_at`, `time_taken`) and peak memory.
- Scheduled Job Log is minimal: it only records status transitions and debug/error output.
- Async Task Log `status` has 6 values vs 4 in Scheduled Job Log; importantly Async Tasks
  distinguishes `Queued` (in RQ waiting for worker) from `Started` (worker picked it up).

---

## 5. Status Lifecycle

### Async Task Log

```
Pending → Queued → Started → Finished
                  ↘ Failed
Pending / Queued / Started → Canceled
```

| Status | When set | Who sets it |
|---|---|---|
| `Pending` | At insert | `enqueue_async_task` / `before_insert` |
| `Queued` | On promotion | Dispatcher (`enqueue_execution`) |
| `Started` | On worker pickup | `execute()` |
| `Finished` | On success | `execute()` |
| `Failed` | On exception | `execute()` / `_save_error()` |
| `Canceled` | On `cancel()` call | Caller / user button |

Every transition publishes a `frappe.realtime` event `async_task_status` to the creating user.

### Scheduled Job Log

```
(Scheduled) → Start → Complete
                    ↘ Failed
```

| Status | When set | Who sets it |
|---|---|---|
| `Scheduled` | At log creation (implicit) | `update_scheduler_log("Scheduled")` — not always called |
| `Start` | When execution begins | `ScheduledJobType.log_status("Start")` |
| `Complete` | On success | `ScheduledJobType.log_status("Complete")` |
| `Failed` | On exception | `ScheduledJobType.log_status("Failed")` |

No realtime event is published. The log is only committed to the database.

---

## 6. Execution Flow

### Async Task

```
enqueue_async_task()
  → insert AsyncTaskLog (status=Pending)
  → after_insert → enqueue_dispatch_async_tasks()   # deduplicated RQ job
      → dispatch_async_tasks() [in worker]
          → filelock(_DISPATCH_LOCK, timeout=0)
          → query Pending tasks ordered by at_front DESC, priority DESC, creation ASC
          → query active counts per method (Queued + Started)
          → for each pending task: check concurrency_limit → enqueue_execution()
              → update_status("Queued")
              → enqueue(execute_task, ...)
                  → execute_task(task_name) [in worker]
                      → task.execute()
                          → update_status("Started")
                          → _execute()  # calls method(**kwargs)
                          → update_status("Finished")
                          → enqueue_dispatch_async_tasks()  # trigger next batch
```

The dispatcher also runs via the `all` scheduler event as a recovery mechanism.

### Scheduled Job

```
frappe scheduler (beat process)
  → ScheduledJobType.enqueue()  [if is_event_due() and not is_job_in_queue()]
      → frappe.enqueue(run_scheduled_job, job_id=rq_job_id)
          → run_scheduled_job(job_type) [in worker]
              → frappe.get_doc("Scheduled Job Type", job_type).execute()
                  → log_status("Start")
                  → execute method (or server_script)
                  → frappe.db.commit()
                  → log_status("Complete")  # or "Failed" on exception
```

---

## 7. Concurrency Control

| | Async Task | Scheduled Job |
|---|---|---|
| **Per-method limit** | `Async Task Type.concurrency_limit` | None |
| **Global deduplication** | Dispatcher filelock prevents duplicate promotions | `rq_job_id = "scheduled_job::<method>"` prevents double-enqueueing the same job type |
| **Overflow behaviour** | Excess tasks stay `Pending` and are promoted on the next dispatch run | Skipped with a scheduler log warning |

---

## 8. Cancellation

| | Async Task | Scheduled Job |
|---|---|---|
| **Supported** | Yes | No |
| **From UI** | Yes (whitelist action on form) | No |
| **From code** | `task.cancel()` | No |
| **Effect on RQ** | `job.stop_job()` if Started; `job.delete()` if Queued | N/A |

---

## 9. Realtime Progress Notifications

| | Async Task | Scheduled Job |
|---|---|---|
| **Event name** | `async_task_status` | — |
| **Payload** | `{name, status, message}` | — |
| **Custom messages** | `task.notify_status(message=...)` or `notify_task_status(message=...)` from inside the job | — |
| **Target** | User who enqueued the task (`frappe.session.user`) | — |

---

## 10. Error Handling

| | Async Task | Scheduled Job |
|---|---|---|
| **Traceback stored on** | `Async Task Log.error_message` | `Scheduled Job Log.details` |
| **DB rollback before error save** | Yes (`frappe.db.rollback()`) | Yes (`frappe.db.rollback()`) |
| **Recovery on connection abort** | `_save_error` decorated with `@dangerously_reconnect_on_connection_abort` | No — log may be lost if connection drops |

---

## 11. Log Cleanup

Both define a `clear_old_logs(days=90)` static method that deletes records older than the given
number of days using `Now() - Interval(days=days)`.

---

## 12. Queue Selection

| | Async Task | Scheduled Job |
|---|---|---|
| **Configurable** | Yes — `queue` field on each task (default / short / long) | Derived from frequency: `long` for `*Long` or `*Maintenance` frequencies, `default` otherwise |
| **Default** | `"default"` | `"default"` |

---

## 13. Source Files

### Async Task (Tweaks)

| File | Role |
|---|---|
| `tweaks/tweaks/doctype/async_task_log/async_task_log.py` | Document controller, `enqueue_async_task`, `enqueue_safe_async_task`, `execute_task` |
| `tweaks/tweaks/doctype/async_task_log/async_task_log_dispatch.py` | `dispatch_async_tasks`, filelock, concurrency algorithm |
| `tweaks/tweaks/doctype/async_task_log/async_task_log.json` | DocType schema |
| `tweaks/tweaks/doctype/async_task_type/async_task_type.py` | Type configuration controller |
| `tweaks/tweaks/doctype/async_task_type/async_task_type.json` | DocType schema |

### Scheduled Job (Frappe Core)

| File | Role |
|---|---|
| `frappe/core/doctype/scheduled_job_type/scheduled_job_type.py` | Document controller, `enqueue`, `execute`, `log_status`, `run_scheduled_job` |
| `frappe/core/doctype/scheduled_job_type/scheduled_job_type.json` | DocType schema |
| `frappe/core/doctype/scheduled_job_log/scheduled_job_log.py` | Document controller, `clear_old_logs` |
| `frappe/core/doctype/scheduled_job_log/scheduled_job_log.json` | DocType schema |
