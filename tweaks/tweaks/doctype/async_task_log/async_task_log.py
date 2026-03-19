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
from uuid import uuid4

import frappe
from frappe import _
from frappe.core.doctype.rq_job.rq_job import RQJob
from frappe.database.utils import dangerously_reconnect_on_connection_abort
from frappe.handler import run_doc_method
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import now, time_diff_in_seconds
from frappe.utils.background_jobs import enqueue
from frappe.utils.safe_exec import call_whitelisted_function
from rq import get_current_job

from tweaks.tweaks.doctype.async_task_log.async_task_log_dispatch import (
    enqueue_dispatch_async_tasks,
    using_dispatcher,
)

AsyncTaskStatus = Literal[
    "Pending", "Paused", "Queued", "Started", "Finished", "Failed", "Canceled"
]


class AsyncTaskLog(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        at_front: DF.Check
        batch_id: DF.Data | None
        batch_order: DF.Int
        debug_log: DF.Code | None
        document_action: DF.Data | None
        document_name: DF.DynamicLink | None
        document_type: DF.Link | None
        ended_at: DF.Datetime | None
        error_message: DF.LongText | None
        job_id: DF.Data | None
        job_name: DF.Data | None
        kwargs: DF.Code | None
        max_retries: DF.Int
        method: DF.Data | None
        queue: DF.Literal["default", "short", "long"]
        retry_count: DF.Int
        retry_delay: DF.Duration | None
        started_at: DF.Datetime | None
        call_whitelisted_function: DF.Check
        status: DF.Literal[
            "Pending", "Paused", "Queued", "Started", "Finished", "Failed", "Canceled"
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

        if self.document_type and self.document_name and self.document_action:
            if not self.method:
                self.method = _derive_document_action_method(
                    self.document_type, self.document_action
                )

        if not self.method:
            frappe.throw(
                _(
                    "Either 'method' or all three of 'document_type', 'document_name', "
                    "and 'document_action' must be provided."
                )
            )

        if not self.job_name:
            self.job_name = self.method

    def after_insert(self):
        if self.flags.get("skip_dispatch") or self.status == "Paused":
            return

        enqueue_dispatch_async_tasks()

    def on_trash(self):
        """
        On Trash event handler
        Based on: frappe.core.doctype.prepared_report.prepared_report.PreparedReport.on_trash
        """
        if self.status in ("Pending", "Paused", "Queued", "Started"):
            self.cancel_job()

    @frappe.whitelist()
    def cancel(self, message=None):
        """
        Cancel a task: if it's Pending or Paused it becomes Canceled; if Queued or Started, the RQ job is stopped/deleted and then the task is marked Canceled.
        """
        if self.status not in ("Pending", "Paused", "Queued", "Started"):
            frappe.throw(_("Cannot cancel task with status {0}").format(self.status))

        self.cancel_job()

        if message:
            frappe.debug_log.extend(["", _("Task canceled with message:"), message])

        self.update_status("Canceled", message=message)

    @frappe.whitelist()
    def toggle_pause(self):
        """
        Toggle a task between Pending and Paused states.

        Pending → Paused: prevents the dispatcher from promoting the task.
        Paused  → Pending: re-queues the task for dispatch.
        """
        if not self.status in ("Pending", "Paused"):
            frappe.throw(
                _(
                    "Only Pending or Paused tasks can be toggled. Current status: {0}"
                ).format(self.status)
            )

        new_status = "Paused" if self.status == "Pending" else "Pending"

        self.update_status(new_status)

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
            self.handle_batch_error()

        enqueue_dispatch_async_tasks()

    def handle_batch_error(self):

        if not self.batch_id:
            return

        with using_dispatcher():
            frappe.debug_log.extend(
                [
                    "",
                    "Task Paused due to error in task:",
                    f"Task: {self.name}",
                    f"Method: {self.method}",
                ]
            )

            tasks = frappe.get_all(
                "Async Task Log",
                filters={
                    "batch_id": self.batch_id,
                    "status": ["in", ["Pending", "Queued", "Started"]],
                },
                pluck="name",
            )
            for task in tasks:
                task = frappe.get_doc("Async Task Log", task)
                if task.status in ("Pending"):
                    task.update_status("Paused")
                elif task.status in ("Queued", "Started"):
                    task.cancel_job()
                    task.update_status("Paused")

    def _execute(self):
        """
        Actual execution logic, separated from status updates and error handling in execute().
        """
        kwargs = json.loads(self.kwargs or "{}")
        if (
            self.document_type
            and self.document_name
            and self.document_action
            and self.call_whitelisted_function
        ):
            run_doc_method(
                method=self.document_action,
                dt=self.document_type,
                dn=self.document_name,
                args=kwargs,
            )
        elif self.document_type and self.document_name and self.document_action:
            doc = frappe.get_doc(self.document_type, self.document_name)
            doc.unlock()
            action = self.document_action
            if hasattr(doc, f"_{action}"):
                action = f"_{action}"
            getattr(doc, action)(**kwargs)
        elif self.call_whitelisted_function:
            call_whitelisted_function(self.method, **kwargs)
        else:
            method = frappe.get_attr(self.method)
            method(**kwargs)

    def update_status(self, status, message=None, error=None):
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
            payload["error_message"] = error
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

        self.notify_status(message=message, error=error)

        self.notify_target_document(message=message, error=error)

    def notify_target_document(self, message=None, error=None):
        if self.document_type and self.document_name:
            try:
                doc = frappe.get_doc(self.document_type, self.document_name)
                doc.run_method(
                    "on_async_task_status_update",
                    task=self,
                    message=message,
                    error=error,
                )
                doc.notify_update()
            except:
                pass

    def notify_status(self, message=None, error=None):
        """
        Publish a realtime message to the user who enqueued the task.

        :param event: Realtime event name
        :param message: Message payload (dict)
        """
        frappe.publish_realtime(
            "async_task_status",
            {
                "name": self.name,
                "status": self.status,
                "message": message,
                "error": error,
            },
            user=frappe.session.user,
        )

    @frappe.whitelist()
    def retry(self, now=False):
        """
        Retry a failed or canceled task: reset it to Pending and trigger dispatch.
        """
        if self.status not in ("Failed", "Canceled"):
            frappe.throw(
                _(
                    "Only Failed or Canceled tasks can be retried. Current status: {0}"
                ).format(self.status)
            )

        self.db_set(
            {
                "status": "Pending",
                "retry_count": (self.retry_count or 0) + 1,
                "error_message": None,
                "debug_log": None,
                "job_id": None,
                "started_at": None,
                "ended_at": None,
                "time_taken": None,
                "peak_memory_usage": 0,
            },
            update_modified=True,
            notify=True,
            commit=True,
        )

        self.notify_status()

        if now:
            self.enqueue_execution()
        else:
            enqueue_dispatch_async_tasks()

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
            job_name=self.job_name or self.method,
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


def _derive_document_action_method(document_type: str, action: str) -> str:
    """
    Derive the dotted Python path for ``action`` on the controller of *document_type*.

    Mirrors the method path used by ``frappe.model.document.execute_action``:
    ``{app}.{module}.doctype.{doctype}.{doctype}.{action}``
    """
    from frappe.modules.utils import get_module_app

    module = frappe.db.get_value("DocType", document_type, "module")
    if not module:
        frappe.throw(frappe._("DocType {0} not found").format(document_type))

    app = get_module_app(module)
    doctype_snake = frappe.scrub(document_type)
    doctype_pascal = "".join(word.capitalize() for word in doctype_snake.split("_"))
    module_snake = frappe.scrub(module)
    return f"{app}.{module_snake}.doctype.{doctype_snake}.{doctype_snake}.{doctype_pascal}.{action}"


def enqueue_async_task(
    method: str | Callable | None = None,
    queue: str = "default",
    timeout: int | None = None,
    *,
    job_name: str | None = None,
    document_type: str | None = None,
    document_name: str | None = None,
    document_action: str | None = None,
    at_front: bool = False,
    call_whitelisted_function: bool = False,
    batch_id: str | None = None,
    batch_order: int | None = None,
    arguments: dict | None = None,
    paused: bool = False,
    max_retries: int = 0,
    retry_delay: int | None = None,
    **kwargs,
) -> "AsyncTaskLog":
    """
    Create an Async Task Log document and trigger dispatch.

    Signature mirrors :func:`frappe.utils.background_jobs.enqueue`.

    :param method: Python dotted path or callable to invoke. Optional when
        *document_type*, *document_name*, and *document_action* are all provided;
        in that case *method* is derived automatically as the doctype controller
        path + ``".{action}"``.
    :param job_name: Human-readable label for the task (used as title). Defaults to *method* when not provided.
    :param document_type: DocType name of the document to act on
    :param document_name: Name of the document to act on
    :param document_action: Method name to call on the document (e.g. ``"submit"``)
    :param queue: RQ queue name (default: ``"default"``)
    :param timeout: Job timeout in seconds (default: 300)
    :param at_front: Whether to run before other pending tasks with the same method
    :param call_whitelisted_function: Run via ``call_whitelisted_function`` instead of direct import
    :param batch_id: Optional batch group identifier; tasks sharing a batch_id are ordered together
    :param batch_order: Position within the batch; lower values dispatch first
    :param arguments: Explicit keyword arguments forwarded to *method*. Takes precedence over
        ``**kwargs`` for keys that collide with the task API parameters (``queue``, ``method``,
        ``timeout``, etc.).
    :param paused: When ``True``, the task is created with status ``"Paused"`` and will not be
        dispatched until :meth:`toggle_pause` is called.
    :param max_retries: Maximum number of automatic retry attempts on failure (default: 0 = no retries).
    :param retry_delay: Delay in seconds before retrying after a failure (Duration field; default: None = retry immediately).
    :param kwargs: Additional keyword arguments forwarded to *method* or the document action
    """
    if callable(method):
        method = f"{method.__module__}.{method.__qualname__}"

    if not method and not (document_type and document_name and document_action):
        raise ValueError(
            "Either 'method' or all three of 'document_type', 'document_name', "
            "and 'document_action' must be provided."
        )

    stored_kwargs = {**kwargs, **(arguments or {})}

    task_data = {
        "doctype": "Async Task Log",
        "queue": queue or "default",
        "method": method,
        "job_name": job_name,
        "document_type": document_type,
        "document_name": document_name,
        "document_action": document_action,
        "kwargs": json.dumps(stored_kwargs),
        "at_front": 1 if at_front else 0,
        "timeout": timeout or 300,
        "call_whitelisted_function": 1 if call_whitelisted_function else 0,
        "batch_id": batch_id,
        "batch_order": batch_order,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
    }
    if paused:
        task_data["status"] = "Paused"

    task = frappe.get_doc(task_data)
    task.insert(ignore_permissions=True)
    # Dispatching is enqueued by the after_insert hook on AsyncTaskLog
    return task


def bulk_enqueue_async_task(
    tasks: list[dict], batch_id: str = None, **kwargs
) -> "AsyncTaskLog":
    """
    Create multiple Async Task Log documents and trigger dispatch.

    Signature mirrors :func:`frappe.utils.background_jobs.enqueue`.

    :param tasks: List of task dictionaries containing method, queue, timeout, at_front, call_whitelisted_function, batch_id, batch_order, and kwargs

    :param kwargs: Keyword arguments to overwrite in each task dict (e.g., to set the same batch_id for all tasks)
    """

    batch_order = 0
    if not batch_id:
        batch_id = str(uuid4())

    with using_dispatcher():

        for task in tasks:
            task.update(**kwargs)
            task["batch_id"] = batch_id
            task["batch_order"] = batch_order
            batch_order += 1

            enqueue_async_task(**task)

    return batch_id


def enqueue_safe_async_task(
    method: str,
    queue: str = "default",
    timeout: int | None = None,
    *,
    job_name: str | None = None,
    at_front: bool = False,
    batch_id: str | None = None,
    batch_order: int | None = None,
    arguments: dict | None = None,
    paused: bool = False,
    max_retries: int = 0,
    retry_delay: int | None = None,
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
        job_name=job_name,
        at_front=at_front,
        call_whitelisted_function=True,
        batch_id=batch_id,
        batch_order=batch_order,
        arguments=arguments,
        paused=paused,
        max_retries=max_retries,
        retry_delay=retry_delay,
        **kwargs,
    )


def bulk_enqueue_safe_async_task(tasks: list[dict], **kwargs) -> "AsyncTaskLog":
    """
    Shorthand for :func:`bulk_enqueue_async_task` with ``call_whitelisted_function=True``.

    Each task's *method* is passed to ``call_whitelisted_function`` at execution time,
    so it must be a whitelisted function or a Server Script name.
    """
    for task in tasks:
        task.pop("call_whitelisted_function", None)
    return bulk_enqueue_async_task(tasks, call_whitelisted_function=True, **kwargs)


@dangerously_reconnect_on_connection_abort
def _save_error(task, error):
    """
    Persist Failed state on the task doc.
    Based on: frappe.core.doctype.prepared_report.prepared_report.PreparedReport._save_error
    """
    task.reload()
    task.update_status("Failed", error=error)


@frappe.request_cache
def get_current_task():

    job = get_current_job()
    if not job:
        return None

    task = frappe.db.exists("Async Task Log", {"job_id": job.id})
    if task:
        return frappe.get_doc("Async Task Log", task)

    return None


def notify_task_status(message):
    """
    Publish a realtime message to the user who enqueued the current task.

    :param message: Message payload (dict)
    """
    task = get_current_task()
    if task:
        task.notify_status(message=message)
