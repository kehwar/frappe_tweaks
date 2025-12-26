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
import requests
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
        # Make POST request to OpenObserve API
        response = requests.post(
            url,
            json=logs,
            headers=headers,
            timeout=30
        )

        # Check for HTTP errors
        response.raise_for_status()

        # Return success response
        return {
            "success": True,
            "response": response.json() if response.text else {},
            "status_code": response.status_code
        }

    except requests.exceptions.RequestException as e:
        # Log the error
        frappe.log_error(
            title=f"OpenObserve API Error - Stream: {stream}",
            message=frappe.get_traceback()
        )

        # Return error response
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                error_msg = f"{error_msg}: {error_details}"
            except:
                error_msg = f"{error_msg}: {e.response.text}"

        frappe.throw(
            f"Failed to send logs to OpenObserve: {error_msg}",
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
