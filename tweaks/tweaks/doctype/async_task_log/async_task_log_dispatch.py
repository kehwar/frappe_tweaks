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

import frappe
from frappe.query_builder import Order
from frappe.utils import add_to_date, now
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

    Used by after_insert and execute_async_task so the dispatcher always runs
    in a worker process rather than in the calling thread.
    """
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
    try:
        with filelock(_DISPATCH_LOCK, timeout=0):
            _run_dispatch()
    except LockTimeoutError:
        return


def _run_dispatch():
    """Execute the dispatch algorithm inside the filelock."""
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
