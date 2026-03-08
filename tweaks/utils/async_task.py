# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Dispatcher and execution utilities for the Async Task system.

Async Task Type (optional) defines per-method configuration: priority and a
concurrency limit. Async Task stores a Python dotted-path method + JSON kwargs
to run as a background job.

Dispatch algorithm:
- A filelock prevents concurrent dispatcher runs; a second call exits immediately.
- Collect all distinct methods that have Pending tasks.
- For each method, look up its Async Task Type (if any) to read priority and
  concurrency limit. Methods without an Async Task Type get priority=0 and no
  concurrency limit.
- Process methods in descending priority order.
- For each method: count active tasks (Queued or Started); if active < limit
  (or no limit), promote Pending tasks up to the available slots.
- Within a method, tasks with at_front=1 run first; ties broken by oldest creation.

Usage::

    from tweaks.utils.async_task import enqueue_async_task

    # Create and immediately dispatch a task
    task = enqueue_async_task(
        method="myapp.utils.process_something",
        kwargs={"doc_name": "INV-0001"},
        queue="default",
        at_front=True,
        timeout=120,
    )
"""

import json

import frappe
from frappe.query_builder import Order
from frappe.utils import now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

_DISPATCH_LOCK = "async_task_dispatch"


def enqueue_async_task(method, kwargs=None, queue="default", at_front=False, timeout=300):
    """
    Create an Async Task document and trigger dispatch.

    Args:
        method: Python dotted path of the function to call
        kwargs: Dict of keyword arguments to pass to the method
        queue: RQ queue name (default: "default")
        at_front: Whether to run before other pending tasks with the same method
        timeout: Job timeout in seconds (default 300)

    Returns:
        Async Task document
    """
    task = frappe.get_doc(
        {
            "doctype": "Async Task",
            "queue": queue or "default",
            "method": method,
            "kwargs": json.dumps(kwargs or {}),
            "at_front": 1 if at_front else 0,
            "timeout": timeout or 300,
        }
    )
    task.insert(ignore_permissions=True)
    # Dispatching is enqueued by the after_insert hook on AsyncTask
    return task


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
    AsyncTask = frappe.qb.DocType("Async Task")

    # Collect distinct methods that have pending tasks
    pending_methods = (
        frappe.qb.from_(AsyncTask)
        .select(AsyncTask.method)
        .where(AsyncTask.status == "Pending")
        .distinct()
        .run(as_list=True)
    )

    if not pending_methods:
        return

    method_names = [row[0] for row in pending_methods]

    # Load Async Task Type configs for all relevant methods in one query
    task_type_configs = {}
    if method_names:
        AsyncTaskType = frappe.qb.DocType("Async Task Type")
        rows = (
            frappe.qb.from_(AsyncTaskType)
            .select(AsyncTaskType.method, AsyncTaskType.priority, AsyncTaskType.limit)
            .where(AsyncTaskType.method.isin(method_names))
            .run(as_dict=True)
        )
        task_type_configs = {r.method: r for r in rows}

    # Build list of (priority, method) and sort by priority DESC
    method_list = []
    for method in method_names:
        cfg = task_type_configs.get(method)
        priority = cfg.priority if cfg else 0
        method_list.append((priority, method))

    method_list.sort(key=lambda x: x[0], reverse=True)

    for _priority, method in method_list:
        cfg = task_type_configs.get(method)
        limit = (cfg.limit or 0) if cfg else 0
        _dispatch_method(method, limit)


def _dispatch_method(method, limit):
    """
    Promote Pending tasks for *method* up to the concurrency limit.

    Args:
        method: Python dotted path identifying the method
        limit: Maximum concurrent tasks (0 = unlimited)
    """
    AsyncTask = frappe.qb.DocType("Async Task")

    # Count active tasks (Queued or Started) for this method
    active_count = (
        frappe.qb.from_(AsyncTask)
        .select(frappe.qb.functions.Count("*"))
        .where(AsyncTask.method == method)
        .where(AsyncTask.status.isin(["Queued", "Started"]))
        .run()[0][0]
    )

    if limit > 0 and active_count >= limit:
        return

    slots = (limit - active_count) if limit > 0 else None  # None = unlimited

    # Build pending query: at_front first, then oldest creation
    query = (
        frappe.qb.from_(AsyncTask)
        .select(AsyncTask.name, AsyncTask.queue, AsyncTask.timeout)
        .where(AsyncTask.method == method)
        .where(AsyncTask.status == "Pending")
        .orderby(AsyncTask.at_front, order=Order.desc)
        .orderby(AsyncTask.creation, order=Order.asc)
    )
    if slots is not None:
        query = query.limit(slots)

    pending = query.run(as_dict=True)

    for task_row in pending:
        _enqueue_task(task_row)


def _enqueue_task(task_row):
    """Set a task to Queued and enqueue it in RQ."""
    frappe.db.set_value(
        "Async Task", task_row.name, "status", "Queued", update_modified=False
    )

    enqueue(
        execute_async_task,
        queue=task_row.queue or "default",
        timeout=task_row.timeout or 300,
        task_name=task_row.name,
        enqueue_after_commit=True,
    )

    frappe.db.commit()


def execute_async_task(task_name):
    """
    Execute an Async Task by name. Runs inside the RQ worker process.

    Args:
        task_name: Name of the Async Task document to execute
    """
    from rq import get_current_job

    rq_job = get_current_job()
    task = frappe.get_doc("Async Task", task_name, for_update=True)

    started = None
    try:
        started = now()
        task.db_set(
            {
                "job_id": rq_job.id if rq_job else None,
                "status": "Started",
                "started_at": started,
            },
            update_modified=False,
            notify=True,
            commit=True,
        )

        kwargs = json.loads(task.kwargs or "{}")
        method = frappe.get_attr(task.method)
        method(**kwargs)

        ended = now()
        task.db_set(
            {
                "status": "Finished",
                "ended_at": ended,
                "time_taken": time_diff_in_seconds(ended, started),
            },
            update_modified=False,
            notify=True,
            commit=True,
        )

    except Exception:
        ended = now()
        task.db_set(
            {
                "status": "Failed",
                "ended_at": ended,
                "time_taken": time_diff_in_seconds(ended, started)
                if started
                else None,
                "error_message": frappe.get_traceback(with_context=True),
            },
            update_modified=False,
            notify=True,
            commit=True,
        )

    finally:
        enqueue_dispatch_async_tasks()
