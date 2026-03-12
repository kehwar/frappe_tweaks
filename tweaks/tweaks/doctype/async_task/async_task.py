# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

"""
Async Task document controller and public API.

Async Task Type (optional) defines per-method configuration: priority and a
concurrency limit. Async Task stores a Python dotted-path method + JSON kwargs
to run as a background job.

Usage::

    from tweaks.tweaks.doctype.async_task.async_task import enqueue_async_task

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
from frappe.utils import add_to_date, now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue
from rq import get_current_job

from tweaks.tweaks.doctype.async_task.async_task_dispatch import (
    enqueue_dispatch_async_tasks,
)

AsyncTaskStatus = Literal[
    "Pending", "Queued", "Started", "Finished", "Failed", "Canceled"
]


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
    method: str | Callable,
    queue: str = "default",
    timeout: int | None = None,
    *,
    at_front: bool = False,
    **kwargs,
) -> "AsyncTask":
    """
    Create an Async Task document and trigger dispatch.

    Signature mirrors :func:`frappe.utils.background_jobs.enqueue`.

    :param method: Python dotted path or callable to invoke
    :param queue: RQ queue name (default: ``"default"``)
    :param timeout: Job timeout in seconds (default: 300)
    :param at_front: Whether to run before other pending tasks with the same method
    :param kwargs: Keyword arguments forwarded to *method*
    """
    if callable(method):
        method = f"{method.__module__}.{method.__qualname__}"

    task = frappe.get_doc(
        {
            "doctype": "Async Task",
            "queue": queue or "default",
            "method": method,
            "kwargs": json.dumps(kwargs),
            "at_front": 1 if at_front else 0,
            "timeout": timeout or 300,
        }
    )
    task.insert(ignore_permissions=True)
    # Dispatching is enqueued by the after_insert hook on AsyncTask
    return task


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
