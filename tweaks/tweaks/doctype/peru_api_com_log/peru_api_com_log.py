# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import json
from typing import Any, Dict, Optional

import frappe
from frappe.core.doctype.log_settings.log_settings import LogType
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class PERUAPICOMLog(Document, LogType):
    """
    Document class for logging PERU API COM service calls.

    This class handles logging of API calls to Peru's services,
    including success responses and error conditions.
    """

    @staticmethod
    def clear_old_logs(days: int = 30) -> None:
        """
        Clear log entries older than specified number of days.

        Args:
                days: Number of days to keep logs (default: 30)
        """
        table = frappe.qb.DocType("PERU API COM Log")
        frappe.db.delete(
            table, filters=(table.modified < (Now() - Interval(days=days)))
        )


def get_data_from_log(endpoint: str, key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached data from previous successful API calls.

    Args:
            endpoint: The API endpoint that was called
            key: The key that was used in the API call

    Returns:
            Dictionary containing cached API response data, or None if not found
    """

    data = frappe.db.get_value(
        "PERU API COM Log",
        filters={"endpoint": endpoint, "key": key, "status": "Success"},
        fieldname="data",
        order_by="creation desc",
    )

    if data:
        return json.loads(data)


def log_api_call(
    endpoint: str,
    key: str,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log an API call result to the database.

    Args:
            endpoint: The API endpoint that was called
            key: The key that was used in the API call
            data: Response data from successful API call (optional)
            error: Error message from failed API call (optional)
    """
    log = frappe.new_doc("PERU API COM Log")
    log.update(
        {
            "endpoint": endpoint,
            "key": key,
            "status": "Success" if data else "Error",
            "data": json.dumps(data) if data else None,
            "error": error,
        }
    )
    log.insert(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist()
def clear_api_logs() -> None:
    """
    Flush all Error Logs.

    This function is whitelisted and can only be called by System Managers.
    It truncates the entire PERU API COM Log table.
    """
    frappe.only_for("System Manager")
    frappe.db.truncate("PERU API COM Log")
