# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import json
from typing import Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.utils import now, time_diff_in_seconds

AsyncTaskStatus = Literal["Pending", "Queued", "Started", "Finished", "Failed", "Canceled"]


class AsyncTask(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        at_front: DF.Check
        ended_at: DF.Datetime | None
        error_message: DF.LongText | None
        job_id: DF.Data | None
        kwargs: DF.Code | None
        method: DF.Data
        queue: DF.Link
        started_at: DF.Datetime | None
        status: DF.Literal["Pending", "Queued", "Started", "Finished", "Failed", "Canceled"]
        time_taken: DF.Duration | None
        timeout: DF.Int
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

        from tweaks.utils.async_task import dispatch_async_tasks

        self.db_set("status", "Pending", update_modified=False)
        frappe.db.commit()
        dispatch_async_tasks()

    def on_trash(self):
        if self.status in ("Pending", "Queued"):
            self.cancel()

    @frappe.whitelist()
    def cancel(self):
        if self.status not in ("Pending", "Queued", "Failed"):
            frappe.throw(_("Cannot cancel task with status {0}").format(self.status))

        if self.job_id:
            try:
                job = frappe.get_doc("RQ Job", self.job_id)
                if self.status == "Queued":
                    job.delete()
            except Exception:
                pass

        self.db_set(
            {"status": "Canceled", "ended_at": now()},
            update_modified=False,
            notify=True,
            commit=True,
        )

    @staticmethod
    def clear_old_logs(days: int = 30) -> None:
        table = frappe.qb.DocType("Async Task")
        frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))
