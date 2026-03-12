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

    from tweaks.tweaks.doctype.async_task.async_task import enqueue_async_task

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
import resource
from contextlib import suppress
from typing import Literal

import frappe
from frappe import _
from frappe.core.doctype.rq_job.rq_job import RQJob
from frappe.database.utils import dangerously_reconnect_on_connection_abort
from frappe.model.document import Document
from frappe.query_builder import Interval, Order
from frappe.query_builder.functions import Now
from frappe.utils import add_to_date, now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock
from rq import get_current_job

AsyncTaskStatus = Literal[
    "Pending", "Queued", "Started", "Finished", "Failed", "Canceled"
]

_DISPATCH_LOCK = "async_task_dispatch"

# If a task stays in Started longer than this it is automatically marked Failed
FAILURE_THRESHOLD = 6 * 60 * 60  # 6 hours


class AsyncTask(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        at_front: DF.Check
        debug_log: DF.Code | None
        ended_at: DF.Datetime | None
        error_message: DF.LongText | None
        job_id: DF.Data | None
        kwargs: DF.Code | None
        method: DF.Data
        queue: DF.Literal["default", "short", "long"]
        started_at: DF.Datetime | None
        status: DF.Literal[
            "Pending", "Queued", "Started", "Finished", "Failed", "Canceled"
        ]
        time_taken: DF.Duration | None
        timeout: DF.Duration | None
        peak_memory_usage: DF.Int
    # end: auto-generated types

    def before_insert(self):
        if not self.status:
            self.status = "Pending"

        if self.kwargs:
            try:
                json.loads(self.kwargs)
            except json.JSONDecodeError as e:
                frappe.throw(_("Invalid kwargs JSON: {0}").format(str(e)))

    def after_insert(self):
        if self.flags.get("skip_dispatch"):
            return

        enqueue_dispatch_async_tasks()

    def on_trash(self):
        """
        On Trash event handler
        Based on: frappe.core.doctype.prepared_report.prepared_report.PreparedReport.on_trash
        """
        if self.status in ("Pending", "Queued", "Started"):
            self.cancel_job()

    @frappe.whitelist()
    def cancel(self):
        """
        Cancel a task: if it's Pending it becomes Canceled; if Queued or Started, the RQ job is stopped/deleted and then the task is marked Canceled.
        """
        if self.status not in ("Pending", "Queued", "Started"):
            frappe.throw(_("Cannot cancel task with status {0}").format(self.status))

        self.cancel_job()

        self.db_set(
            {"status": "Canceled", "ended_at": now()},
            update_modified=True,
            notify=True,
            commit=True,
        )

    def cancel_job(self):
        """
        Cancel the RQ job associated with this task, if any.
        Based on: frappe.core.doctype.prepared_report.prepared_report.PreparedReport.on_trash
        """
        with suppress(Exception):
            job: RQJob = frappe.get_doc("RQ Job", self.job_id)
            job.stop_job() if self.status == "Started" else job.delete()

    @staticmethod
    def clear_old_logs(days=90):
        """
        Clear Async Tasks that ended more than `days` ago.
        Based on: frappe.core.doctype.scheduled_job_log.scheduled_job_log.ScheduledJobLog.clear_old_logs
        """
        table = frappe.qb.DocType("Async Task")
        frappe.db.delete(
            table, filters=(table.modified < (Now() - Interval(days=days)))
        )

    def execute(self):
        """
        Execute this task. Runs inside the RQ worker process.

        Based on:
            frappe.core.doctype.scheduled_job_type.scheduled_job_type.ScheduledJobType.execute
            frappe.core.doctype.prepared_report.prepared_report.generate_report
        """
        try:
            self.update_status("Started")
            kwargs = json.loads(self.kwargs or "{}")
            method = frappe.get_attr(self.method)
            method(**kwargs)
            frappe.db.commit()
            self.update_status("Finished")
        except Exception:
            frappe.db.rollback()
            _save_error(self, error=frappe.get_traceback(with_context=True))

        frappe.publish_realtime(
            "async_task_complete",
            {"name": self.name, "status": self.status},
            user=frappe.session.user,
        )

        enqueue_dispatch_async_tasks()

    def update_status(self, status):
        """
        Persist task status to the database and update in-memory state.

        Based on: frappe.core.doctype.scheduled_job_type.scheduled_job_type.ScheduledJobType.update_scheduler_log
        """
        frappe.logger("async_task").info(
            f"Async Task {status}: {self.method} for {frappe.local.site}"
        )

        payload = {"status": status}

        if frappe.debug_log:
            payload["debug_log"] = "\n".join(frappe.debug_log)
        if status == "Failed":
            payload["error_message"] = frappe.get_traceback(with_context=True)
        if status == "Started":
            job = get_current_job()
            payload["job_id"] = job.id if job else None
            payload["started_at"] = now()
        if status == "Finished":
            payload["ended_at"] = now()
            if self.started_at:
                payload["time_taken"] = time_diff_in_seconds(
                    payload["ended_at"], self.started_at
                )
            payload["peak_memory_usage"] = resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss

        self.db_set(payload, update_modified=False, notify=True, commit=True)


def enqueue_async_task(
    method, kwargs=None, queue="default", at_front=False, timeout=300
):
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
        limit = (cfg.concurrency_limit or 0) if cfg else 0
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
    Convenience function to execute an Async Task by name.

    Loads the Async Task document and calls its execute() method.
    Intended to be enqueued as an RQ background job by the dispatcher.

    Args:
        task_name: Name of the Async Task document to execute
    """
    task = frappe.get_doc("Async Task", task_name)
    task.execute()


@dangerously_reconnect_on_connection_abort
def _save_error(task, error):
    """
    Persist Failed state on the task doc.
    Based on: frappe.core.doctype.prepared_report.prepared_report.PreparedReport._save_error
    """
    task.reload()
    task.status = "Failed"
    task.error_message = error
    task.save(ignore_permissions=True)


def expire_stalled_tasks():
    """
    Mark tasks that have been Started longer than FAILURE_THRESHOLD as Failed.
    Based on: frappe.core.doctype.prepared_report.prepared_report.expire_stalled_reports
    """
    frappe.db.set_value(
        "Async Task",
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
