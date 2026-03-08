# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from tweaks.utils.async_task import (
    _dispatch_method,
    _run_dispatch,
    dispatch_async_tasks,
    enqueue_async_task,
    enqueue_dispatch_async_tasks,
)


def _make_task_type(method, priority=0, limit=0):
    """Create an Async Task Type doc if it does not already exist."""
    if not frappe.db.exists("Async Task Type", method):
        frappe.get_doc(
            {
                "doctype": "Async Task Type",
                "method": method,
                "priority": priority,
                "limit": limit,
            }
        ).insert(ignore_permissions=True)
    return frappe.get_doc("Async Task Type", method)


def _make_task(method="frappe.utils.now", queue="default", kwargs=None, at_front=False):
    """Insert a Pending Async Task without triggering the after_insert dispatcher."""
    task = frappe.get_doc(
        {
            "doctype": "Async Task",
            "queue": queue,
            "method": method,
            "kwargs": json.dumps(kwargs or {}),
            "at_front": 1 if at_front else 0,
            "timeout": 60,
            "status": "Pending",
        }
    )
    task.flags.skip_dispatch = True
    task.insert(ignore_permissions=True)
    return task


class TestAsyncTaskType(FrappeTestCase):
    """Basic sanity check for the Async Task Type doctype."""

    def setUp(self):
        frappe.db.rollback()

    def test_task_type_created_with_fields(self):
        t = _make_task_type("tweaks.utils.async_task.execute_async_task", priority=5, limit=3)
        self.assertEqual(t.priority, 5)
        self.assertEqual(t.limit, 3)


class TestDispatcher(FrappeTestCase):
    """Tests for dispatch_async_tasks dispatcher logic."""

    def setUp(self):
        frappe.db.rollback()

    def test_pending_task_is_queued(self):
        """A single pending task with no task type should be promoted to Queued."""
        method = "tweaks.test.method.single"
        task = _make_task(method=method)

        with patch("tweaks.utils.async_task.enqueue"):
            _dispatch_method(method, limit=0)

        status = frappe.db.get_value("Async Task", task.name, "status")
        self.assertEqual(status, "Queued")

    def test_limit_is_respected(self):
        """Only `limit` tasks should be promoted at a time."""
        method = "tweaks.test.method.limit"
        [_make_task(method=method) for _ in range(4)]

        with patch("tweaks.utils.async_task.enqueue"):
            _dispatch_method(method, limit=2)

        queued = frappe.db.count("Async Task", {"method": method, "status": "Queued"})
        pending = frappe.db.count("Async Task", {"method": method, "status": "Pending"})
        self.assertEqual(queued, 2)
        self.assertEqual(pending, 2)

    def test_at_front_runs_first(self):
        """Tasks with at_front=1 should be promoted before normal pending tasks."""
        method = "tweaks.test.method.at_front"
        normal_task = _make_task(method=method, at_front=False)
        front_task = _make_task(method=method, at_front=True)

        with patch("tweaks.utils.async_task.enqueue"):
            _dispatch_method(method, limit=1)

        self.assertEqual(frappe.db.get_value("Async Task", front_task.name, "status"), "Queued")
        self.assertEqual(frappe.db.get_value("Async Task", normal_task.name, "status"), "Pending")

    def test_no_slots_when_active_fills_limit(self):
        """No tasks should be promoted when active count >= limit."""
        method = "tweaks.test.method.full"
        started = _make_task(method=method)
        frappe.db.set_value("Async Task", started.name, "status", "Started")

        pending = _make_task(method=method)

        with patch("tweaks.utils.async_task.enqueue") as mock_enqueue:
            _dispatch_method(method, limit=1)
            mock_enqueue.assert_not_called()

        self.assertEqual(frappe.db.get_value("Async Task", pending.name, "status"), "Pending")

    def test_unlimited_when_no_limit(self):
        """limit=0 means unlimited: all pending tasks should be promoted."""
        method = "tweaks.test.method.unlimited"
        tasks = [_make_task(method=method) for _ in range(5)]

        with patch("tweaks.utils.async_task.enqueue"):
            _dispatch_method(method, limit=0)

        for t in tasks:
            self.assertEqual(frappe.db.get_value("Async Task", t.name, "status"), "Queued")

    def test_task_type_priority_orders_methods(self):
        """Higher-priority methods should be dispatched before lower-priority ones."""
        method_hi = "tweaks.test.method.priority_hi"
        method_lo = "tweaks.test.method.priority_lo"
        _make_task_type(method_hi, priority=10, limit=1)
        _make_task_type(method_lo, priority=1, limit=1)

        _make_task(method=method_hi)
        _make_task(method=method_lo)

        dispatched = []

        def fake_dispatch(method, limit):
            dispatched.append(method)

        with patch("tweaks.utils.async_task._dispatch_method", side_effect=fake_dispatch):
            _run_dispatch()

        hi_idx = dispatched.index(method_hi)
        lo_idx = dispatched.index(method_lo)
        self.assertLess(hi_idx, lo_idx)

    def test_dispatch_exits_when_locked(self):
        """dispatch_async_tasks should exit immediately if the filelock is held."""
        import fcntl

        with patch("tweaks.utils.async_task.fcntl") as mock_fcntl:
            mock_fcntl.LOCK_EX = fcntl.LOCK_EX
            mock_fcntl.LOCK_NB = fcntl.LOCK_NB
            mock_fcntl.LOCK_UN = fcntl.LOCK_UN
            mock_fcntl.flock.side_effect = BlockingIOError

            with patch("tweaks.utils.async_task._run_dispatch") as mock_run:
                dispatch_async_tasks()
                mock_run.assert_not_called()


class TestEnqueueAsyncTask(FrappeTestCase):
    """Tests for the enqueue_async_task helper."""

    def setUp(self):
        frappe.db.rollback()

    def test_creates_task_document(self):
        with patch("tweaks.utils.async_task.enqueue"):
            task = enqueue_async_task(
                method="frappe.utils.now",
                kwargs={"foo": "bar"},
                queue="default",
                timeout=120,
            )

        self.assertTrue(frappe.db.exists("Async Task", task.name))
        self.assertEqual(task.method, "frappe.utils.now")
        self.assertEqual(task.queue, "default")
        loaded = frappe.get_doc("Async Task", task.name)
        self.assertEqual(json.loads(loaded.kwargs), {"foo": "bar"})

    def test_after_insert_enqueues_dispatch(self):
        """Inserting an Async Task should enqueue dispatch, not call it directly."""
        with patch("tweaks.utils.async_task.enqueue") as mock_enqueue:
            task = enqueue_async_task(
                method="frappe.utils.now",
                queue="default",
            )

        mock_enqueue.assert_called_once_with(
            dispatch_async_tasks, queue="default", enqueue_after_commit=True
        )
