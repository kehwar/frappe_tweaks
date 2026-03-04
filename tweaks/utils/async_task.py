# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Dispatcher and execution utilities for the Async Task system.

Async Task Queue defines named queues with a priority and a concurrency limit.
Async Task stores a Python dotted-path method + JSON kwargs to run as a
background job.

Dispatch algorithm:
- Queues are processed in descending priority order.
- For each queue, count tasks currently in Queued or Started state.
- If running < limit, promote Pending tasks to Queued (up to limit - running).
- Within a queue, tasks with at_front=1 run first; ties broken by oldest creation.

Usage::

    import frappe
    from tweaks.utils.async_task import enqueue_async_task

    # Create and immediately dispatch a task
    task = enqueue_async_task(
        queue="default",
        method="myapp.utils.my_function",
        kwargs={"arg1": "value1"},
    )
"""

import json

import frappe
from frappe.query_builder import Order
from frappe.utils import now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue


def enqueue_async_task(queue, method, kwargs=None, at_front=False, timeout=300):
    """
    Create an Async Task document and trigger dispatch.

    Args:
        queue: Name of Async Task Queue
        method: Python dotted path of the function to call
        kwargs: Dict of keyword arguments to pass to the method
        at_front: Whether to run before other pending tasks in the queue
        timeout: Job timeout in seconds (default 300)

    Returns:
        Async Task document
    """
    task = frappe.get_doc(
        {
            "doctype": "Async Task",
            "queue": queue,
            "method": method,
            "kwargs": json.dumps(kwargs or {}),
            "at_front": 1 if at_front else 0,
            "timeout": timeout or 300,
        }
    )
    task.insert(ignore_permissions=True)
    # Dispatching is triggered by the after_insert hook on AsyncTask
    return task


def dispatch_async_tasks():
    """
    Promote pending tasks to Queued and enqueue them respecting queue limits.

    Called after a task is created or after a task finishes/fails.
    Also called by the scheduled job to recover from any missed triggers.
    """
    AsyncTaskQueue = frappe.qb.DocType("Async Task Queue")
    queues = (
        frappe.qb.from_(AsyncTaskQueue)
        .select(AsyncTaskQueue.name, AsyncTaskQueue.priority, AsyncTaskQueue.limit)
        .orderby(AsyncTaskQueue.priority, order=Order.desc)
        .run(as_dict=True)
    )

    for queue in queues:
        _dispatch_queue(queue)


def _dispatch_queue(queue):
    """Promote Pending tasks in *queue* up to the concurrency limit."""
    limit = queue.limit or 1
    queue_name = queue.name

    AsyncTask = frappe.qb.DocType("Async Task")

    # Count active tasks (Queued or Started)
    active_count = (
        frappe.qb.from_(AsyncTask)
        .select(frappe.qb.functions.Count("*"))
        .where(AsyncTask.queue == queue_name)
        .where(AsyncTask.status.isin(["Queued", "Started"]))
        .run()[0][0]
    )

    slots = limit - active_count
    if slots <= 0:
        return

    # Find pending tasks: at_front first, then oldest creation
    pending = (
        frappe.qb.from_(AsyncTask)
        .select(AsyncTask.name, AsyncTask.timeout)
        .where(AsyncTask.queue == queue_name)
        .where(AsyncTask.status == "Pending")
        .orderby(AsyncTask.at_front, order=Order.desc)
        .orderby(AsyncTask.creation, order=Order.asc)
        .limit(slots)
        .run(as_dict=True)
    )

    for task_row in pending:
        _enqueue_task(task_row)


def _enqueue_task(task_row):
    """Set a task to Queued and enqueue it in RQ."""
    frappe.db.set_value(
        "Async Task", task_row.name, "status", "Queued", update_modified=False
    )

    enqueue(
        execute_async_task,
        queue="default",
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
        dispatch_async_tasks()
