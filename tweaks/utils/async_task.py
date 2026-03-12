# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

# Backward-compatibility shim. All logic has moved to the doctype module.
# Import from the canonical location instead:
#   from tweaks.tweaks.doctype.async_task.async_task import enqueue_async_task

from tweaks.tweaks.doctype.async_task.async_task import (  # noqa: F401
    FAILURE_THRESHOLD,
    _DISPATCH_LOCK,
    _dispatch_method,
    _enqueue_task,
    _run_dispatch,
    _save_error,
    dispatch_async_tasks,
    enqueue_async_task,
    enqueue_dispatch_async_tasks,
    execute_async_task,
    expire_stalled_tasks,
    update_job_id,
)
from frappe.utils.background_jobs import enqueue  # noqa: F401
from frappe.utils.synchronization import filelock  # noqa: F401
