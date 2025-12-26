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

Example Usage:
    # Send logs to OpenObserve
    send_logs(
        stream="application-logs",
        logs=[{"message": "Test log", "level": "info"}],
        org="default"
    )
"""

import json
from typing import Any, Dict, List, Optional

import frappe
from frappe.integrations.utils import make_get_request, make_post_request
from frappe.model.document import Document


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
        self,
        stream: str,
        logs: List[Dict[str, Any]],
        org: Optional[str] = None
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
    stream: str,
    logs: List[Dict[str, Any]],
    org: Optional[str] = None
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

    # Build API URL
    # OpenObserve API format: {url}/api/{org}/{stream}/_json
    url = f"{config.url.rstrip('/')}/api/{organization}/{stream}/_json"

    # Get authentication header
    headers = config.get_auth_header()
    headers["Content-Type"] = "application/json"

    try:
        # Make POST request to OpenObserve API using Frappe's integration utility
        response = make_post_request(
            url,
            data=json.dumps(logs),
            headers=headers
        )

        # Return success response
        return {
            "success": True,
            "response": response,
            "status_code": 200
        }

    except Exception as e:
        # Log the error
        frappe.log_error(
            title=f"OpenObserve API Error - Stream: {stream}",
            message=frappe.get_traceback()
        )

        # Return error response
        frappe.throw(
            f"Failed to send logs to OpenObserve: {str(e)}",
            title="API Error"
        )


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
            logs=[{
                "message": "Test connection from Frappe Tweaks",
                "timestamp": frappe.utils.now(),
                "level": "info"
            }]
        )

        return {
            "success": True,
            "message": "Connection test successful",
            "details": result
        }

    except Exception as e:
        return {
            "success": False,
            "message": "Connection test failed",
            "error": str(e)
        }


@frappe.whitelist()
def search_logs(
    stream: str,
    query: Optional[Dict[str, Any]] = None,
    org: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    size: int = 100
) -> Dict[str, Any]:
    """
    Search logs in OpenObserve stream.

    This function is whitelisted and can only be called by System Managers.
    It searches log data from an OpenObserve stream based on query parameters.

    Args:
        stream: Stream name to search logs from
        query: SQL query or query object for filtering logs (optional)
        org: Organization name (optional, uses default_org from config if not provided)
        start_time: Start time for log search in ISO format (optional)
        end_time: End time for log search in ISO format (optional)
        size: Maximum number of logs to return (default: 100)

    Returns:
        Dictionary containing API response with keys:
        - success: Boolean indicating if the operation was successful
        - response: The API response data with search results
        - status_code: HTTP status code

    Raises:
        frappe.PermissionError: If the current user is not a System Manager
        Exception: If the API call fails

    Example:
        >>> # Search logs from last hour
        >>> search_logs(
        ...     stream="application-logs",
        ...     start_time="2025-12-26T05:00:00Z",
        ...     end_time="2025-12-26T06:00:00Z",
        ...     size=50
        ... )

        >>> # Search with custom query
        >>> search_logs(
        ...     stream="error-logs",
        ...     query={"sql": "SELECT * FROM error_logs WHERE level='error'"},
        ...     size=100
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
    # OpenObserve API format: {url}/api/{org}/{stream}/_search
    url = f"{config.url.rstrip('/')}/api/{organization}/{stream}/_search"

    # Get authentication header
    headers = config.get_auth_header()
    headers["Content-Type"] = "application/json"

    # Build search parameters
    params = {}
    if size:
        params["size"] = size
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    try:
        # Make GET request to OpenObserve API using Frappe's integration utility
        if query:
            # If query is provided, use POST request
            response = make_post_request(
                url,
                data=json.dumps(query),
                headers=headers,
                params=params
            )
        else:
            # Otherwise use GET request with params
            response = make_get_request(
                url,
                headers=headers,
                params=params
            )

        # Return success response
        return {
            "success": True,
            "response": response,
            "status_code": 200
        }

    except Exception as e:
        # Log the error
        frappe.log_error(
            title=f"OpenObserve API Error - Search Stream: {stream}",
            message=frappe.get_traceback()
        )

        # Return error response
        frappe.throw(
            f"Failed to search logs in OpenObserve: {str(e)}",
            title="API Error"
        )
