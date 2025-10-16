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

    def restore_defaults(self, only_if_missing: bool = False):

        if not self.website_url or (not only_if_missing):
            self.website_url = self.meta.get_field("website_url").default
        if not self.ruc_url or (not only_if_missing):
            self.ruc_url = self.meta.get_field("ruc_url").default
        if not self.dni_url or (not only_if_missing):
            self.dni_url = self.meta.get_field("dni_url").default
        if not self.tc_url or (not only_if_missing):
            self.tc_url = self.meta.get_field("tc_url").default
        if not self.auth_header or (not only_if_missing):
            self.auth_header = self.meta.get_field("auth_header").default
        self.cache = self.meta.get_field("cache").default

    def validate_setup(self):

        if not self.token:
            frappe.throw("El token de autenticación es obligatorio.")

        if not self.auth_header:
            frappe.throw("El encabezado de autenticación es obligatorio.")

        if not self.website_url:
            frappe.throw("La URL del sitio web es obligatoria.")

        if not self.ruc_url:
            frappe.throw("La URL del servicio RUC es obligatoria.")

        if not self.dni_url:
            frappe.throw("La URL del servicio DNI es obligatoria.")

        if not self.tc_url:
            frappe.throw("La URL del servicio TC es obligatoria.")


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
    doc.restore_defaults(only_if_missing=True)
    doc.validate_setup()

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
        # Use caching is enabled and requested by the caller
        if cache and use_cache():
            data = get_data_from_log(endpoint, key)
            if data:
                log_api_call(endpoint, key, data=data, cache=True)
                return data

        # Build the request parameters (URL, headers, auth tokens)
        kwargs = get_kwargs(endpoint, key, param)

        # Make the actual HTTP GET request to the Peru API
        data = make_get_request(**kwargs)

        # Log successful API response if caching is enabled
        if use_cache():
            log_api_call(endpoint, key, data=data)

        # Return the API response data
        return data
    except Exception as e:
        traceback = frappe.get_traceback()

        # Log the failed API call with error details
        log_api_call(endpoint, key, error=traceback)

        # Raise a user-friendly error with context about what failed
        frappe.throw(
            [
                frappe._("Error searching {0}: {1}").format(endpoint.upper(), key),
                "---",
                *traceback.split("\n"),
            ],
            exc=e,
            title=frappe._("API Error"),
            wide=1,
            as_list=1,
        )


@frappe.whitelist()
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


@frappe.whitelist()
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


@frappe.whitelist()
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


@frappe.whitelist()
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


@frappe.whitelist()
def restore_defaults(only_if_missing: bool = False):

    frappe.only_for("System Manager")

    doc = frappe.get_doc("PERU API COM")

    doc.restore_defaults(only_if_missing)

    doc.save()


@frappe.whitelist()
def get_default_settings():

    frappe.only_for("System Manager")

    doc = frappe.get_doc("PERU API COM")
    doc.restore_defaults()

    return doc.as_dict()
