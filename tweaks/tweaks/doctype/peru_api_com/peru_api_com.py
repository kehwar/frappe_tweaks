# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

from datetime import date
from typing import Any, Dict, Optional, Union

import frappe
from frappe.integrations.utils import make_get_request
from frappe.model.document import Document
from frappe.utils import format_date, getdate
from requests.exceptions import HTTPError

from tweaks.tweaks.doctype.peru_api_com_log.peru_api_com_log import (
    get_data_from_log,
    log_api_call,
)


class PERUAPICOM(Document):
    """
    Document class for PERU API COM integration.

    This class provides methods to interact with Peru's API services
    for retrieving RUT, RUC, DNI, and exchange rate (TC) information.
    """

    def get_rut(self, rut: str, cache: bool = True) -> Dict[str, Any]:
        """
        Get RUT information from Peru API.

        Args:
                rut: The RUT number to look up
                cache: Whether to use cached data if available

        Returns:
                Dictionary containing RUT information
        """
        return get_rut(rut, cache)

    def get_ruc(self, ruc: str, cache: bool = True) -> Dict[str, Any]:
        """
        Get RUC information from Peru API.

        Args:
                ruc: The RUC number to look up
                cache: Whether to use cached data if available

        Returns:
                Dictionary containing RUC information
        """
        return get_ruc(ruc, cache)

    def get_dni(self, dni: str, cache: bool = True) -> Dict[str, Any]:
        """
        Get DNI information from Peru API.

        Args:
                dni: The DNI number to look up
                cache: Whether to use cached data if available

        Returns:
                Dictionary containing DNI information
        """
        return get_dni(dni, cache)

    def get_tc(
        self, date: Optional[Union[str, date]] = None, cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get exchange rate (tipo de cambio) information from Peru API.

        Args:
                date: The date to get exchange rate for (defaults to current date)
                cache: Whether to use cached data if available

        Returns:
                Dictionary containing exchange rate information
        """
        return get_tc(date, cache)


def use_cache() -> bool:
    """
    Check if caching is enabled for the PERU API COM service.

    Returns:
            True if caching is enabled, False otherwise
    """
    return frappe.get_cached_value("PERU API COM", "PERU API COM", "cache")


def get_kwargs(
    endpoint: str, key: Optional[str] = None, param: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build request kwargs for API calls.

    Args:
            endpoint: The API endpoint name
            key: The key value for the request
            param: The parameter name for query-based requests

    Returns:
            Dictionary containing URL, headers, and parameters for the request
    """

    doc = frappe.get_cached_doc("PERU API COM")
    doc.token = doc.get_password("token")

    url = doc.get(f"{endpoint}_url")

    if param:
        return {
            "url": url,
            "headers": {
                "Authorization": f"Bearer {doc.token}",
                doc.auth_header: doc.token,
            },
            "params": {param: key},
        }
    return {
        "url": f"{url}/{key}",
        "headers": {
            "Authorization": f"Bearer {doc.token}",
            doc.auth_header: doc.token,
        },
    }


def _make_api_call(
    endpoint: str,
    key: Optional[str] = None,
    cache: bool = True,
    param: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generic function to make API calls with caching and logging.

    Args:
            endpoint: The API endpoint to call
            key: The key value for the request
            cache: Whether to use cached data if available
            param: The parameter name for query-based requests

    Returns:
            Dictionary containing API response data

    Raises:
            Exception: If the API call fails, with appropriate error message
    """
    try:
        if cache and use_cache():
            data = get_data_from_log(endpoint, key)
            if data:
                return data

        kwargs = get_kwargs(endpoint, key, param)

        data = make_get_request(**kwargs)

        if use_cache():
            log_api_call(endpoint, key, data=data)
        return data
    except Exception as e:
        reason = ""
        if isinstance(e, HTTPError) and e.response is not None and e.response.reason:
            reason = e.response.reason
        else:
            reason = str(e)
        log_api_call(endpoint, key, error=reason)
        frappe.throw(reason, exc=e, title=f"Error al buscar {endpoint.upper()}: {key}")


def get_rut(rut: str, cache: bool = True) -> Dict[str, Any]:
    """
    Get RUT information. Routes to DNI or RUC based on length.

    Args:
            rut: The RUT number (8 digits for DNI, more for RUC)
            cache: Whether to use cached data if available

    Returns:
            Dictionary containing RUT information
    """
    if len(rut) == 8:
        return get_dni(rut, cache)
    else:
        return get_ruc(rut, cache)


def get_ruc(ruc: str, cache: bool = True) -> Dict[str, Any]:
    """
    Get RUC (company registration) information from Peru API.

    Args:
            ruc: The RUC number to look up
            cache: Whether to use cached data if available

    Returns:
            Dictionary containing RUC information
    """
    return _make_api_call("ruc", key=ruc, cache=cache)


def get_dni(dni: str, cache: bool = True) -> Dict[str, Any]:
    """
    Get DNI (national ID) information from Peru API.

    Args:
            dni: The DNI number to look up
            cache: Whether to use cached data if available

    Returns:
            Dictionary containing DNI information
    """
    return _make_api_call("dni", key=dni, cache=cache)


def get_tc(
    date: Optional[Union[str, date]] = None, cache: bool = True
) -> Dict[str, Any]:
    """
    Get exchange rate (tipo de cambio) information from Peru API.

    Args:
            date: The date to get exchange rate for (defaults to current date)
            cache: Whether to use cached data if available

    Returns:
            Dictionary containing exchange rate information
    """
    date = getdate(date)
    date = format_date(date, "yyyy-mm-dd")

    return _make_api_call("tc", key=date, param="fecha", cache=cache)
