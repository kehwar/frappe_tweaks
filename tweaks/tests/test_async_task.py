# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from tweaks.utils.async_task import (
    _dispatch_queue,
    dispatch_async_tasks,
    enqueue_async_task,
)


def _make_queue(name, priority=0, limit=1):
    if not frappe.db.exists("Async Task Queue", name):
        frappe.get_doc(
            {
                "doctype": "Async Task Queue",
                "queue_name": name,
                "priority": priority,
                "limit": limit,
            }
        ).insert(ignore_permissions=True)
    return frappe.get_doc("Async Task Queue", name)


def _make_task(queue_name, method="frappe.utils.now", kwargs=None, at_front=False):
    task = frappe.get_doc(
        {
            "doctype": "Async Task",
            "queue": queue_name,
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


class TestAsyncTaskQueue(FrappeTestCase):
    """Tests for Async Task Queue doctype"""

    def setUp(self):
        frappe.db.rollback()

    def test_queue_created_with_defaults(self):
        q = _make_queue("test-queue-defaults", priority=5, limit=3)
        self.assertEqual(q.priority, 5)
        self.assertEqual(q.limit, 3)


class TestDispatcher(FrappeTestCase):
    """Tests for dispatch_async_tasks dispatcher logic"""

    def setUp(self):
        frappe.db.rollback()

    def test_pending_task_is_queued(self):
        """A single pending task should be promoted to Queued"""
        q = _make_queue("test-dispatch-single", priority=0, limit=1)
        task = _make_task(q.name)

        with patch("tweaks.utils.async_task.enqueue") as mock_enqueue:
            _dispatch_queue({"name": q.name, "priority": 0, "limit": 1})

        status = frappe.db.get_value("Async Task", task.name, "status")
        self.assertEqual(status, "Queued")

    def test_limit_is_respected(self):
        """Only `limit` tasks should be promoted at a time"""
        q = _make_queue("test-dispatch-limit", priority=0, limit=2)
        tasks = [_make_task(q.name) for _ in range(4)]

        with patch("tweaks.utils.async_task.enqueue"):
            _dispatch_queue({"name": q.name, "priority": 0, "limit": 2})

        queued = frappe.db.count(
            "Async Task", {"queue": q.name, "status": "Queued"}
        )
        pending = frappe.db.count(
            "Async Task", {"queue": q.name, "status": "Pending"}
        )
        self.assertEqual(queued, 2)
        self.assertEqual(pending, 2)

    def test_at_front_runs_first(self):
        """Tasks with at_front=1 should be promoted before normal pending tasks"""
        q = _make_queue("test-dispatch-at-front", priority=0, limit=1)
        normal_task = _make_task(q.name, at_front=False)
        front_task = _make_task(q.name, at_front=True)

        with patch("tweaks.utils.async_task.enqueue"):
            _dispatch_queue({"name": q.name, "priority": 0, "limit": 1})

        front_status = frappe.db.get_value("Async Task", front_task.name, "status")
        normal_status = frappe.db.get_value("Async Task", normal_task.name, "status")
        self.assertEqual(front_status, "Queued")
        self.assertEqual(normal_status, "Pending")

    def test_no_slots_when_active_fills_limit(self):
        """No tasks should be promoted when active count >= limit"""
        q = _make_queue("test-dispatch-full", priority=0, limit=1)
        # Simulate a started task
        started = _make_task(q.name)
        frappe.db.set_value("Async Task", started.name, "status", "Started")

        pending = _make_task(q.name)

        with patch("tweaks.utils.async_task.enqueue") as mock_enqueue:
            _dispatch_queue({"name": q.name, "priority": 0, "limit": 1})
            mock_enqueue.assert_not_called()

        status = frappe.db.get_value("Async Task", pending.name, "status")
        self.assertEqual(status, "Pending")


class TestEnqueueAsyncTask(FrappeTestCase):
    """Tests for the enqueue_async_task helper"""

    def setUp(self):
        frappe.db.rollback()

    def test_creates_task_document(self):
        _make_queue("test-enqueue-helper", priority=0, limit=5)

        with patch("tweaks.utils.async_task.enqueue"):
            task = enqueue_async_task(
                queue="test-enqueue-helper",
                method="frappe.utils.now",
                kwargs={"foo": "bar"},
                timeout=120,
            )

        self.assertTrue(frappe.db.exists("Async Task", task.name))
        self.assertEqual(task.method, "frappe.utils.now")
        loaded = frappe.get_doc("Async Task", task.name)
        self.assertEqual(json.loads(loaded.kwargs), {"foo": "bar"})
