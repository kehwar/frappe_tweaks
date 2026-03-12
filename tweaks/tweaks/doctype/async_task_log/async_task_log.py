# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Async Task Log document controller and public API.

Async Task Type (optional) defines per-method configuration: priority and a
concurrency limit. Async Task Log stores a Python dotted-path method + JSON kwargs
to run as a background job.

Usage::

    from tweaks.tweaks.doctype.async_task_log.async_task_log import enqueue_async_task

    # Create and immediately dispatch a task
    task = enqueue_async_task(
        "myapp.utils.process_something",
        queue="default",
        at_front=True,
        timeout=120,
        doc_name="INV-0001",
    )
"""

import json
import resource
from collections.abc import Callable
from contextlib import suppress
from typing import Literal

import frappe
from frappe import _
from frappe.core.doctype.rq_job.rq_job import RQJob
from frappe.database.utils import dangerously_reconnect_on_connection_abort
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue
from rq import get_current_job

from tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch import (
    enqueue_dispatch_async_tasks,
)

AsyncTaskStatus = Literal[
    "Pending", "Queued", "Started", "Finished", "Failed", "Canceled"
]


class AsyncTaskLog(Document):
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
        call_whitelisted_function: DF.Check
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

        self.update_status("Canceled")

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
        Clear Async Task Logs that ended more than `days` ago.
        Based on: frappe.core.doctype.scheduled_job_log.scheduled_job_log.ScheduledJobLog.clear_old_logs
        """
        table = frappe.qb.DocType("Async Task Log")
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
            self._execute()
            frappe.db.commit()
            self.update_status("Finished")
        except Exception:
            frappe.db.rollback()
            _save_error(self, error=frappe.get_traceback(with_context=True))

        enqueue_dispatch_async_tasks()

    def _execute(self):
        """
        Actual execution logic, separated from status updates and error handling in execute().
        """
        kwargs = json.loads(self.kwargs or "{}")
        if self.call_whitelisted_function:
            from frappe.utils.safe_exec import call_whitelisted_function

            call_whitelisted_function(self.method, **kwargs)
        else:
            method = frappe.get_attr(self.method)
            method(**kwargs)

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
        if status in ("Finished", "Failed", "Canceled"):
            payload["ended_at"] = now()
            if self.started_at:
                payload["time_taken"] = time_diff_in_seconds(
                    payload["ended_at"], self.started_at
                )
            payload["peak_memory_usage"] = resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss

        self.db_set(payload, update_modified=True, notify=True, commit=True)

        self.notify_status()

    def notify_status(self, message=None):
        """
        Publish a realtime message to the user who enqueued the task.

        :param event: Realtime event name
        :param message: Message payload (dict)
        """
        frappe.publish_realtime(
            "async_task_status",
            {"name": self.name, "status": self.status, "message": message},
            user=frappe.session.user,
        )

    @frappe.whitelist()
    def enqueue_execution(self):

        if self.status != "Pending":
            frappe.throw(_("Only Pending tasks can be enqueued."))

        self.update_status("Queued")

        enqueue(
            execute_task,
            queue=self.queue or "default",
            timeout=self.timeout or 300,
            at_front=bool(self.at_front),
            job_name=self.method,
            enqueue_after_commit=True,
            task_name=self.name,
        )


def execute_task(task_name):
    """
    Execute a task by name. To be called by the RQ worker process.
    """
    task = frappe.get_doc("Async Task Log", task_name)
    task.unlock()
    task.execute()


def enqueue_async_task(
    method: str | Callable,
    queue: str = "default",
    timeout: int | None = None,
    *,
    at_front: bool = False,
    call_whitelisted_function: bool = False,
    **kwargs,
) -> "AsyncTaskLog":
    """
    Create an Async Task Log document and trigger dispatch.

    Signature mirrors :func:`frappe.utils.background_jobs.enqueue`.

    :param method: Python dotted path or callable to invoke
    :param queue: RQ queue name (default: ``"default"``)
    :param timeout: Job timeout in seconds (default: 300)
    :param at_front: Whether to run before other pending tasks with the same method
    :param call_whitelisted_function: Run via ``call_whitelisted_function`` instead of direct import
    :param kwargs: Keyword arguments forwarded to *method*
    """
    if callable(method):
        method = f"{method.__module__}.{method.__qualname__}"

    task = frappe.get_doc(
        {
            "doctype": "Async Task Log",
            "queue": queue or "default",
            "method": method,
            "kwargs": json.dumps(kwargs),
            "at_front": 1 if at_front else 0,
            "timeout": timeout or 300,
            "call_whitelisted_function": 1 if call_whitelisted_function else 0,
        }
    )
    task.insert(ignore_permissions=True)
    # Dispatching is enqueued by the after_insert hook on AsyncTaskLog
    return task


def enqueue_safe_async_task(
    method: str,
    queue: str = "default",
    timeout: int | None = None,
    *,
    at_front: bool = False,
    **kwargs,
) -> "AsyncTaskLog":
    """
    Shorthand for :func:`enqueue_async_task` with ``call_whitelisted_function=True``.

    *method* is passed to ``call_whitelisted_function`` at execution time,
    so it must be a whitelisted function or a Server Script name.
    """
    kwargs.pop("call_whitelisted_function", None)
    return enqueue_async_task(
        method,
        queue=queue,
        timeout=timeout,
        at_front=at_front,
        call_whitelisted_function=True,
        **kwargs,
    )


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
