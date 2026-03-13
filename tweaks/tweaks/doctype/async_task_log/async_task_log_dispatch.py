# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Dispatch logic for the Async Task Log system.

Dispatch algorithm:
- A filelock prevents concurrent dispatcher runs; a second call exits immediately.
- Collect all Pending tasks joined with their Async Task Type (if any).
- Order tasks by: at_front DESC, priority DESC, creation ASC.
- Track active task counts per method (Queued or Started).
- For each pending task in order: if its method has a concurrency_limit and
  the active count is at or above that limit, skip it; otherwise enqueue it
  and increment the in-memory active count.
"""

from contextlib import contextmanager

import frappe
from frappe.query_builder import Order
from frappe.utils import add_to_date, cint, now, sbool
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock
from pypika.functions import Coalesce, Count

_DISPATCH_LOCK = "async_task_dispatch"

# If a task stays in Started longer than this it is automatically marked Failed
FAILURE_THRESHOLD = 6 * 60 * 60  # 6 hours


def enqueue_dispatch_async_tasks():
    """
    Enqueue dispatch_async_tasks as a background job.

    Used by after_insert so the dispatcher always runs
    in a worker process rather than in the calling thread.
    """
    if not can_dispatch_now():
        return

    enqueue(
        dispatch_async_tasks,
        queue="default",
        enqueue_after_commit=True,
        job_name="dispatch_async_tasks",
        job_id="dispatch_async_tasks",
        deduplicate=True,
    )


def dispatch_async_tasks():
    """
    Promote pending tasks to Queued and enqueue them respecting method limits.

    Protected by a non-blocking filelock (timeout=0): if another dispatcher is
    already running, this call exits immediately to avoid duplicate promotions.

    Called by the scheduler (all event) to recover from any missed triggers,
    and via enqueue_dispatch_async_tasks after task creation/completion.
    """
    if not can_dispatch_now():
        return

    with using_dispatcher(timeout=0):
        _run_dispatch()


def _run_dispatch():
    """Execute the dispatch algorithm inside the filelock."""
    retry_failed_tasks()

    AsyncTask = frappe.qb.DocType("Async Task Log")
    AsyncTaskType = frappe.qb.DocType("Async Task Type")

    # All pending tasks joined with their type config, ordered for execution
    pending_tasks = (
        frappe.qb.from_(AsyncTask)
        .left_join(AsyncTaskType)
        .on(AsyncTask.method == AsyncTaskType.method)
        .select(
            AsyncTask.name,
            AsyncTask.method,
            AsyncTask.queue,
            AsyncTask.timeout,
            AsyncTask.at_front,
            AsyncTaskType.concurrency_limit,
        )
        .where(AsyncTask.status == "Pending")
        .orderby(AsyncTask.at_front, order=Order.desc)
        .orderby(Coalesce(AsyncTaskType.priority, 0), order=Order.desc)
        .orderby(AsyncTask.batch_id, order=Order.asc)
        .orderby(Coalesce(AsyncTask.batch_order, 999999), order=Order.asc)
        .orderby(AsyncTask.creation, order=Order.asc)
        .run(as_dict=True)
    )

    if not pending_tasks:
        return

    # Active counts per method (Queued or Started)
    active_counts = {}
    active_rows = (
        frappe.qb.from_(AsyncTask)
        .select(AsyncTask.method, Count("*").as_("cnt"))
        .where(AsyncTask.status.isin(["Queued", "Started"]))
        .groupby(AsyncTask.method)
        .run(as_dict=True)
    )
    for row in active_rows:
        active_counts[row.method] = row.cnt

    for task in pending_tasks:
        method = task.method
        limit = task.concurrency_limit or 0
        active = active_counts.get(method, 0)

        if limit > 0 and active >= limit:
            continue

        _enqueue_task(task)
        active_counts[method] = active + 1


def _enqueue_task(task_row):
    """Set a task to Queued and enqueue it in RQ."""

    task = frappe.get_doc("Async Task Log", task_row.name)
    task.enqueue_execution()


def expire_stalled_tasks():
    """
    Mark tasks that have been Started longer than FAILURE_THRESHOLD as Failed.
    Based on: frappe.core.doctype.prepared_report.prepared_report.expire_stalled_reports
    """
    frappe.db.set_value(
        "Async Task Log",
        {
            "status": "Started",
            "modified": (
                "<",
                add_to_date(now(), seconds=-FAILURE_THRESHOLD, as_datetime=True),
            ),
        },
        {
            "status": "Failed",
            "error_message": frappe._("Task timed out."),
        },
        update_modified=False,
    )


def retry_failed_tasks():
    """
    Automatically retry failed tasks that have remaining retry attempts and whose
    retry delay has elapsed since the last failure.

    Queries all Failed tasks where ``retry_count < max_retries``, then retries
    those whose ``retry_delay`` (stored in seconds as a Duration field) has passed
    since ``modified`` (the timestamp of the last failure).
    """
    AsyncTask = frappe.qb.DocType("Async Task Log")

    tasks = (
        frappe.qb.from_(AsyncTask)
        .select(AsyncTask.name, AsyncTask.retry_delay, AsyncTask.modified)
        .where(AsyncTask.status == "Failed")
        .where(AsyncTask.max_retries > 0)
        .where(AsyncTask.retry_count < AsyncTask.max_retries)
        .run(as_dict=True)
    )

    current_time = now()
    for task_row in tasks:
        retry_delay = cint(task_row.retry_delay or 0)
        if retry_delay > 0 and task_row.modified:
            retry_after = add_to_date(task_row.modified, seconds=retry_delay)
            if retry_after > current_time:
                continue

        try:
            task = frappe.get_doc("Async Task Log", task_row.name)
            task.retry()
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Auto-retry failed for Async Task Log {task_row.name}",
            )


def can_dispatch_now():
    """
    Check if dispatching is currently allowed based on the "suspend_async_task_dispatch" default.
    Based on: frappe.email.doctype.email_queue.email_queue.EmailQueue.can_send_now
    """
    if cint(frappe.db.get_default("suspend_async_task_dispatch")) == 1:
        return False

    return True


def _set_dispatcher_state(enabled):
    """
    Persist the dispatcher suspension flag without permission checks.

    Internal helper used by :func:`toggle_dispatcher` (public, permission-gated)
    and :func:`bulk_enqueue_async_task` (may run in a worker context).
    """
    frappe.db.set_default("suspend_async_task_dispatch", 0 if enabled else 1)


@frappe.whitelist()
def toggle_dispatcher(enable):
    """
    Enable or disable the async task dispatcher.

    Requires System Manager role. Persists the state as a site default so it
    survives process restarts.

    :param enable: Truthy → resume dispatching; falsy → suspend dispatching.

    Based on: frappe.email.doctype.email_queue.email_queue.toggle_sending
    """
    frappe.only_for("System Manager")
    _set_dispatcher_state(sbool(enable))


@contextmanager
def using_dispatcher(timeout=30):
    """
    Context manager that suspends the dispatcher on entry and resumes it on exit.

    Acquires the dispatch filelock (waiting up to `timeout` seconds for any in-progress dispatcher
    to finish) so no concurrent dispatch can run for the duration of the block.
    On exit the dispatcher is resumed and a single dispatch pass is enqueued.

    Use this when bulk-inserting tasks that should not be dispatched individually
    as they are created, then trigger a single dispatch pass afterwards::

        with using_dispatcher(timeout=30):
            for item in items:
                enqueue_async_task(...)
        # dispatcher is resumed here; enqueue_dispatch_async_tasks is called automatically
    """
    try:
        with filelock(_DISPATCH_LOCK, timeout=timeout):
            dispatcher_paused = False
            if can_dispatch_now():
                dispatcher_paused = True
                _set_dispatcher_state(False)
            try:
                yield
            finally:
                if dispatcher_paused:
                    _set_dispatcher_state(True)
                    enqueue_dispatch_async_tasks()
    except LockTimeoutError:
        pass
