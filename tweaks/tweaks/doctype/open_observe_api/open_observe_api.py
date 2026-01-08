# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

"""
OpenObserve API Integration Module

This module provides integration with OpenObserve, an open-source observability platform
for logs, metrics, and traces. It enables sending log data to OpenObserve streams for
monitoring and analysis.

Main Classes:
    OpenObserveAPI: Document class for API configuration and method access

Main Functions:
    send_logs: Send log data to an OpenObserve stream
    search_logs: Search and query logs from OpenObserve
    test_connection: Test connection to OpenObserve API

Example Usage:
    # Send logs to OpenObserve
    send_logs(
        stream="application-logs",
        logs=[{"message": "Test log", "level": "info"}],
        org="default"
    )

    # Search logs
    search_logs(
        sql="SELECT * FROM application_logs WHERE level='error'",
        start_time="2025-01-01T00:00:00Z",
        end_time="2025-01-01T23:59:59Z"
    )
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import frappe
from frappe.integrations.utils import make_get_request, make_post_request
from frappe.model.document import Document
from frappe.utils import convert_timezone_to_utc, get_datetime


class OpenObserveAPI(Document):
    """
    Document class for OpenObserve API integration.

    This class provides methods to interact with OpenObserve, an open-source
    observability platform for sending logs, metrics, and traces.
    """

    def validate_setup(self) -> None:
        """
        Validate that all required configuration fields are set.

        Raises:
            frappe.ValidationError: If any required field is missing
        """
        if not self.url:
            frappe.throw("URL is required.")

        if not self.user:
            frappe.throw("User is required.")

        if not self.password:
            frappe.throw("Password is required.")

    def get_auth_header(self) -> Dict[str, str]:
        """
        Get authentication header for API requests.

        Returns:
            Dictionary containing Basic Auth header
        """
        password = self.get_password("password")
        # OpenObserve uses Basic Auth with user:password encoded in base64
        import base64

        credentials = f"{self.user}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    def send_logs(
        self, stream: str, logs: List[Dict[str, Any]], org: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send logs to OpenObserve stream.

        Args:
            stream: Stream name to send logs to
            logs: List of log dictionaries to send
            org: Organization name (uses default_org if not provided)

        Returns:
            Dictionary containing API response
        """
        return send_logs(stream, logs, org)


def get_api_config() -> OpenObserveAPI:
    """
    Get OpenObserve API configuration.

    Returns:
        OpenObserveAPI document with configuration

    Raises:
        frappe.ValidationError: If configuration is invalid
    """
    doc = frappe.get_cached_doc("Open Observe API")
    doc.validate_setup()
    return doc


@frappe.whitelist()
def send_logs(
    stream: str, logs: List[Dict[str, Any]], org: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send logs to OpenObserve stream.

    This function is whitelisted and can only be called by System Managers.
    It sends log data to an OpenObserve stream for monitoring and analysis.

    Args:
        stream: Stream name to send logs to
        logs: List of log dictionaries to send. Each log can contain any fields.
        org: Organization name (optional, uses default_org from config if not provided)

    Returns:
        Dictionary containing API response with keys:
        - success: Boolean indicating if the operation was successful
        - response: The API response data
        - status_code: HTTP status code

    Raises:
        frappe.PermissionError: If the current user is not a System Manager
        Exception: If the API call fails

    Example:
        >>> # Send a single log entry
        >>> send_logs(
        ...     stream="application-logs",
        ...     logs=[{
        ...         "message": "User login successful",
        ...         "level": "info",
        ...         "user": "john@example.com",
        ...         "timestamp": "2025-12-26T02:20:00Z"
        ...     }]
        ... )

        >>> # Send multiple log entries with custom organization
        >>> send_logs(
        ...     stream="error-logs",
        ...     logs=[
        ...         {"message": "Error occurred", "level": "error", "code": 500},
        ...         {"message": "Retry failed", "level": "error", "code": 503}
        ...     ],
        ...     org="production"
        ... )
    """
    # Only System Managers can send logs
    frappe.only_for("System Manager")

    # Parse logs if it's a JSON string (from client-side calls)
    if isinstance(logs, str):
        logs = json.loads(logs)

    # Get API configuration
    config = get_api_config()

    # Use provided org or default from config
    organization = org or config.default_org or "default"

    # Add environment suffix to organization
    if not org:
        if frappe.conf.developer_mode:
            organization = f"{organization}.dev"
        elif frappe.flags.in_test:
            organization = f"{organization}.test"

    # Build API URL
    # OpenObserve API format: {url}/api/{org}/{stream}/_json
    url = f"{config.url.rstrip('/')}/api/{organization}/{stream}/_json"

    # Get authentication header
    headers = config.get_auth_header()
    headers["Content-Type"] = "application/json"

    try:
        # Make POST request to OpenObserve API using Frappe's integration utility
        response = make_post_request(
            url, data=frappe.as_json(logs, indent=0), headers=headers
        )

        status = response.get("status") or []
        successful = 0
        failed = 0
        error_message = None
        for item in status:
            if item.get("successful", 0) > 0:
                successful += item.get("successful", 0)
            if item.get("failed", 0) > 0:
                failed += item.get("failed", 0)
                error_message = item.get("error", "Unknown error")

        if failed > 0:
            return {
                "success": False,
                "response": response,
                "error": error_message,
                "successful": successful,
                "failed": failed,
            }

        return {
            "success": True,
            "response": response,
            "successful": successful,
            "failed": failed,
        }

    except Exception as e:
        # Log the error
        frappe.log_error(
            title=f"OpenObserve API Error - Stream: {stream}",
            message=frappe.get_traceback(),
        )

        # Return error response
        frappe.throw(f"Failed to send logs to OpenObserve: {str(e)}", title="API Error")


@frappe.whitelist()
def test_connection() -> Dict[str, Any]:
    """
    Test connection to OpenObserve API.

    This function is whitelisted and can only be called by System Managers.
    It sends a test log entry to verify the configuration is correct.

    Returns:
        Dictionary with test results

    Raises:
        frappe.PermissionError: If the current user is not a System Manager
    """
    frappe.only_for("System Manager")

    try:
        # Send a test log entry
        result = send_logs(
            stream="test-connection",
            logs=[
                {
                    "message": "Test connection from Frappe Tweaks",
                    "timestamp": frappe.utils.now(),
                    "level": "info",
                }
            ],
        )

        return {
            "success": True,
            "message": "Connection test successful",
            "details": result,
        }

    except Exception as e:
        return {"success": False, "message": "Connection test failed", "error": str(e)}


@frappe.whitelist()
def search_logs(
    query: Optional[Dict[str, Any]] = None,
    stream: Optional[str] = None,
    sql: Optional[str] = None,
    org: Optional[str] = None,
    start_time: Optional[Union[str, datetime, int]] = None,
    end_time: Optional[Union[str, datetime, int]] = None,
    start: Optional[int] = None,
    size: Optional[int] = None,
    search_type: str = "ui",
    timeout: int = 0,
) -> Dict[str, Any]:
    """
    Search logs in OpenObserve stream.

    This function is whitelisted and can only be called by System Managers.
    It searches log data from OpenObserve using SQL queries and time ranges.

    Args:
        query: Query object that can be complete or incomplete. Missing fields will be filled
               from individual parameters. Can contain sql, start_time, end_time, start, size.
               Time values can be ISO strings, datetime objects, or Unix timestamps in microseconds. (optional)
        stream: Stream name to search logs from (optional, used to replace {stream} placeholder in sql)
        sql: SQL query string for filtering logs (e.g., "SELECT * FROM stream_name WHERE level='error'").
             Use {stream} placeholder which will be replaced with the actual stream name. (optional)
        org: Organization name (optional, uses default_org from config if not provided)
        start_time: Start time for log search. Accepts:
                    - ISO format string (e.g., "2025-12-26T05:00:00Z")
                    - datetime object (naive or timezone-aware)
                    - Unix timestamp in microseconds (int)
                    Naive datetimes are converted to UTC. (optional)
        end_time: End time for log search. Accepts same formats as start_time. (optional)
        start: Starting offset for pagination (default: 0 if not in query object)
        size: Maximum number of logs to return (default: 100 if not in query object)
        search_type: Type of search, typically "ui" (default: "ui")
        timeout: Query timeout in seconds (default: 0 for no timeout)

    Returns:
        Dictionary containing API response with keys:
        - success: Boolean indicating if the operation was successful
        - response: The API response data with search results
        - status_code: HTTP status code

    Raises:
        frappe.PermissionError: If the current user is not a System Manager
        frappe.ValidationError: If sql, start_time, or end_time are missing in final query
        Exception: If the API call fails

    Example:
        >>> # Search with complete query object (Unix timestamps)
        >>> search_logs(
        ...     query={
        ...         "sql": "SELECT * FROM application_logs",
        ...         "start_time": 1674789786006000,
        ...         "end_time": 1674789886006000,
        ...         "start": 0,
        ...         "size": 100
        ...     }
        ... )

        >>> # Search with incomplete query object, completed with parameters
        >>> search_logs(
        ...     query={"sql": "SELECT * FROM application_logs"},
        ...     start_time="2025-12-26T05:00:00Z",
        ...     end_time="2025-12-26T06:00:00Z",
        ...     size=50
        ... )

        >>> # Search with individual parameters only (ISO strings)
        >>> search_logs(
        ...     stream="application-logs",
        ...     sql="SELECT * FROM {stream} WHERE level='error'",
        ...     start_time="2025-12-26T05:00:00Z",
        ...     end_time="2025-12-26T06:00:00Z",
        ...     size=50
        ... )

        >>> # Search with datetime objects
        >>> from datetime import datetime, timedelta
        >>> search_logs(
        ...     sql="SELECT * FROM error_logs",
        ...     start_time=datetime.now() - timedelta(hours=1),
        ...     end_time=datetime.now()
        ... )

        >>> # Parameter override - query provides base, parameters override
        >>> search_logs(
        ...     query={"sql": "SELECT * FROM logs", "start_time": "2025-01-01T00:00:00Z"},
        ...     end_time="2025-01-01T23:59:59Z",  # Completes missing end_time
        ...     size=200  # Overrides default size
        ... )
    """
    # Only System Managers can search logs
    frappe.only_for("System Manager")

    # Parse query if it's a JSON string (from client-side calls)
    if isinstance(query, str):
        query = json.loads(query)

    # Get API configuration
    config = get_api_config()

    # Use provided org or default from config
    organization = org or config.default_org or "default"

    # Build API URL for search
    # OpenObserve API format: {url}/api/{org}/_search
    url = f"{config.url.rstrip('/')}/api/{organization}/_search"

    # Get authentication header
    headers = config.get_auth_header()
    headers["Content-Type"] = "application/json"

    # Start with query object if provided, otherwise start fresh
    query_obj = query.copy() if query else {}

    # Individual parameters always override query object values when provided

    # Override start and size if parameters are provided
    if start is not None:
        query_obj["start"] = start
    elif "start" not in query_obj:
        query_obj["start"] = 0  # Default value

    if size is not None:
        query_obj["size"] = size
    elif "size" not in query_obj:
        query_obj["size"] = 100  # Default value

    # Override SQL query if sql parameter is provided
    if sql:
        query_obj["sql"] = sql
    elif stream and "sql" not in query_obj:
        # If no SQL in query object and no sql parameter, generate default query using stream
        query_obj["sql"] = f"SELECT * FROM {stream}"

    # Replace {stream} placeholder in SQL if stream is provided
    if stream and "sql" in query_obj:
        query_obj["sql"] = query_obj["sql"].replace("{stream}", stream)

    # Override time range if parameters are provided
    if start_time is not None:
        query_obj["start_time"] = start_time

    if end_time is not None:
        query_obj["end_time"] = end_time

    # Convert start_time and end_time to Unix timestamps in microseconds if needed
    if "start_time" in query_obj:
        dt = None
        if isinstance(query_obj["start_time"], str):
            dt = get_datetime(query_obj["start_time"])
        elif isinstance(query_obj["start_time"], datetime):
            dt = query_obj["start_time"]

        if dt is not None:
            # Convert naive datetime to UTC before converting to timestamp
            dt = convert_timezone_to_utc(dt)
            query_obj["start_time"] = int(dt.timestamp() * 1000000)

    if "end_time" in query_obj:
        dt = None
        if isinstance(query_obj["end_time"], str):
            dt = get_datetime(query_obj["end_time"])
        elif isinstance(query_obj["end_time"], datetime):
            dt = query_obj["end_time"]

        if dt is not None:
            # Convert naive datetime to UTC before converting to timestamp
            dt = convert_timezone_to_utc(dt)
            query_obj["end_time"] = int(dt.timestamp() * 1000000)

    # Build final request body
    request_body = {
        "query": query_obj,
        "search_type": search_type,
        "timeout": timeout,
    }

    # Validate that required fields are present in the final query
    if "sql" not in request_body["query"]:
        frappe.throw("'sql' is required in the query")
    if "start_time" not in request_body["query"]:
        frappe.throw("'start_time' is required in the query")
    if "end_time" not in request_body["query"]:
        frappe.throw("'end_time' is required in the query")

    try:
        # Make POST request to OpenObserve API using Frappe's integration utility
        response = make_post_request(
            url, data=frappe.as_json(request_body, indent=0), headers=headers
        )

        # Return success response
        return {"success": True, "response": response, "status_code": 200}

    except Exception as e:
        # Log the error
        frappe.log_error(
            title=f"OpenObserve API Error - Search Stream: {stream}",
            message=frappe.get_traceback(),
        )

        # Return error response
        frappe.throw(
            f"Failed to search logs in OpenObserve: {str(e)}", title="API Error"
        )
