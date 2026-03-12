<!-- ============================================================
  COMPARISON TEMPLATE — Async Task Log vs {SYSTEM_NAME}
  ============================================================
  Usage:
    1. Copy this file → comparison_with_{system_slug}.md
    2. Replace every {PLACEHOLDER} with real content.
    3. Remove template instructions (HTML comment blocks).
    4. Mark rows that don't apply with "N/A" or omit the row.
    5. System-specific extra sections go between section 11
       and section 12 (e.g. "## 11a. Result / Output Handling").
  ============================================================ -->

# Async Task Log vs {SYSTEM_NAME} — Comparison

<!-- 1–2 sentences: what {SYSTEM_NAME} is, and when to consult this document. -->

---

## 1. Purpose & Trigger Model

| Dimension | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Triggered by** | Application code (`enqueue_async_task`) | {…} |
| **Who initiates** | Any code path, agent, or user action | {…} |
| **Repetition** | One-shot | {one-shot / recurring / …} |
| **Primary use case** | On-demand background work with visibility | {…} |

---

## 2. DocType Roles

| Role | Async Task system | {SYSTEM_NAME} |
|---|---|---|
| **Configuration** | `Async Task Type` (optional, per method) | {…} |
| **Execution log** | `Async Task Log` | {…} |
| **Link between them** | `async_task_log.job_id` | {…} |

---

## 3. Schema

<!-- Use a single side-by-side table when schemas are compact.
     Split into ### 3a / ### 3b subsections when each schema is large
     and needs its own field-by-field breakdown. -->

| Field | Async Task Log | {SYSTEM_NAME} |
|---|---|---|
| **Naming** | `autoname: hash` | {…} |
| Method / callable | `method` (Data) — dotted path or Server Script | {…} |
| `status` | `Select`: Pending / Queued / Started / Finished / Failed / Canceled | {…} |
| `queue` | `Select`: default / short / long | {…} |
| `timeout` | Duration | {…} |
| `job_id` | Data (set on Queued) | {…} |
| `kwargs` | JSON | {…} |
| `started_at` | Datetime | {…} |
| `ended_at` | Datetime | {…} |
| `time_taken` | Duration (computed) | {…} |
| `peak_memory_usage` | Int (RSS KB) | {…} |
| `error_message` | Code (full traceback) | {…} |
| `debug_log` | Code (`frappe.debug_log`) | {…} |
| `at_front` | Check | {…} |
| `call_whitelisted_function` | Check | {…} |
| `owner` | standard Frappe field (enqueueing user) | {…} |

---

## 4. Status Lifecycle

### Async Task Log

```
Pending → Queued → Started → Finished
                           ↘ Failed
          ↘ Canceled  (cancelable from Pending, Queued, or Started)
```

- **Pending** — dispatcher-managed; task created but not yet pushed to RQ.
- **Queued** — RQ job created; `job_id` populated.
- **Started / Finished / Failed** — mirror underlying RQ job states.
- **Canceled** — explicit cancellation from any pre-terminal state.

### {SYSTEM_NAME}

```
{state diagram}
```

<!-- Describe each state and any notable differences from Async Task. -->

---

## 5. Execution Flow

### Async Task Log

```
enqueue_async_task()
  → insert AsyncTaskLog (status=Pending)
    → after_insert → enqueue_dispatch_async_tasks()
        → dispatch_async_tasks() [in worker]
            → concurrency check + priority ordering
            → enqueue_execution() → update_status("Queued")
                → execute_task(task_name) [in worker]
                    → task.execute()
```

### {SYSTEM_NAME}

```
{trigger / entry point}
  → {step 1}
      → {step 2}
          → {execution}
```

---

## 6. Key Differences

| Concern | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Persistence** | Permanent MariaDB record | {…} |
| **Pre-queue waiting** | `Pending` state + dispatcher | {…} |
| **Concurrency control** | `Async Task Type.concurrency_limit` | {…} |
| **Priority ordering** | `priority` + `at_front` | {…} |
| **Realtime events** | Every status transition | {…} |
| **Cancellation** | Full (Pending / Queued / Started) | {…} |
| **Observability** | timing, memory, debug log, traceback | {…} |

---

## 7. Concurrency & Priority

| Concern | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Per-method limit** | `Async Task Type.concurrency_limit` | {…} |
| **Priority ordering** | `Async Task Type.priority` + per-task `at_front` | {…} |
| **Deduplication** | Dispatcher filelock | {…} |
| **Overflow behaviour** | Tasks stay `Pending` until next dispatch | {…} |

---

## 8. Cancellation

| | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Supported** | Yes | {…} |
| **From UI** | Yes | {…} |
| **From code** | `task.cancel()` | {…} |
| **Effect on RQ** | `stop_job()` if Started; `delete()` if Queued | {…} |
| **Cancelable states** | Pending, Queued, Started | {…} |
| **Post-cancel status** | `Canceled` | {…} |

---

## 9. Realtime Notifications

| | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Event name** | `async_task_status` | {…} |
| **Payload** | `{name, status, message}` | {…} |
| **Frequency** | Every status transition | {…} |
| **Custom messages** | `task.notify_status(message=...)` or `notify_task_status(message=...)` | {…} |
| **Target** | User who enqueued the task | {…} |

---

## 10. Error Handling

| | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Traceback stored on** | `Async Task Log.error_message` | {…} |
| **DB rollback before save** | Yes (`frappe.db.rollback()`) | {…} |
| **Connection abort recovery** | `@dangerously_reconnect_on_connection_abort` | {…} |
| **Stalled task reaper** | Yes — `expire_stalled_tasks()` after 6 h | {…} |

---

## 11. Log Cleanup

| | Async Task | {SYSTEM_NAME} |
|---|---|---|
| **Retention** | 90 days (default) | {…} |
| **Schedule** | `daily_long` scheduler event | {…} |
| **Mechanism** | `AsyncTaskLog.clear_old_logs(days=90)` | {…} |

---

<!-- ## N. [System-specific section]
     Optional — insert system-specific sections here, before section 12.
     Examples: Result / Output Handling, Queue Selection. -->

---

## 12. When to Choose Each

Use **Async Task** when:
- {reason 1}
- {reason 2}

Use **{SYSTEM_NAME}** when:
- {reason 1}
- {reason 2}

---

## 13. Source Files

| Component | Path |
|---|---|
| Async Task Log controller | `tweaks/tweaks/doctype/async_task_log/async_task_log.py` |
| Async Task Log schema | `tweaks/tweaks/doctype/async_task_log/async_task_log.json` |
| Async Task dispatch | `tweaks/tweaks/doctype/async_task_log/async_task_log_dispatch.py` |
| Async Task Type | `tweaks/tweaks/doctype/async_task_type/async_task_type.py` |
| {SYSTEM_NAME} controller | `{path}` |
| {SYSTEM_NAME} schema | `{path}` |
