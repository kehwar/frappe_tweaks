# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

"""
PERU API COM Integration Module

This module provides integration with PERU API COM, a private API service for retrieving
various types of information about Peru including:
- RUT (tax identification number) information
- RUC (company registration) information and branch details
- DNI (national ID) information
- Exchange rates (tipo de cambio)

The module implements caching functionality to reduce API calls and includes
comprehensive logging for monitoring and debugging purposes.

Main Classes:
    PERUAPICOM: Document class for API configuration and method access

Main Functions:
    get_rut: Retrieve RUT information (routes to DNI or RUC based on length)
    get_ruc: Retrieve RUC company information
    get_ruc_suc: Retrieve RUC branch information
    get_dni: Retrieve DNI personal information
    get_tc: Retrieve exchange rate information

Example Usage:
    # Get company information
    ruc_data = get_ruc("20123456789", cache=True)

    # Get personal information
    dni_data = get_dni("12345678", cache=True)

    # Get exchange rate for specific date
    tc_data = get_tc("2025-01-01", cache=True)
"""

from datetime import date
from typing import Any, Dict, Optional, Union

import frappe
from erpnext.setup.doctype.currency_exchange.currency_exchange import CurrencyExchange
from frappe.contacts.doctype.address.address import Address
from frappe.integrations.utils import make_get_request
from frappe.model.document import Document
from frappe.utils import format_date, getdate
from requests.exceptions import HTTPError

from tweaks.custom.doctype.customer import make_address
from tweaks.tweaks.doctype.peru_api_com_log.peru_api_com_log import (
    get_data_from_log,
    log_api_call,
)


class PERUAPICOM(Document):
    """
    Document class for PERU API COM integration.

    This class provides methods to interact with PERU API COM, a private API service
    for retrieving RUT, RUC, DNI, and exchange rate (TC) information for Peru.
    """

    def get_rut(self, rut: str, cache: bool = True) -> Dict[str, Any]:
        """
        Get RUC or DNI information.
        """
        return get_rut(rut, cache)

    def get_ruc(
        self, ruc: str, cache: bool = True, sucursales: bool = False
    ) -> Dict[str, Any]:
        """
        Get RUC information.
        """
        return get_ruc(ruc, cache=cache, sucursales=sucursales)

    def get_ruc_suc(self, ruc: str, cache: bool = True) -> Dict[str, Any]:
        return get_ruc_suc(ruc, cache)

    def get_dni(self, dni: str, cache: bool = True) -> Dict[str, Any]:
        """
        Get DNI information.
        """
        return get_dni(dni, cache)

    def get_tc(
        self, date: Optional[Union[str, date]] = None, cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get exchange rate information.
        """
        return get_tc(date, cache)

    def restore_defaults(self, only_if_missing: bool = False) -> None:
        """
        Restore default values for API configuration fields.

        Args:
            only_if_missing: If True, only restore fields that are empty
        """
        if not self.website_url or (not only_if_missing):
            self.website_url = self.meta.get_field("website_url").default
        if not self.ruc_url or (not only_if_missing):
            self.ruc_url = self.meta.get_field("ruc_url").default
        if not self.ruc_suc_url or (not only_if_missing):
            self.ruc_suc_url = self.meta.get_field("ruc_suc_url").default
        if not self.dni_url or (not only_if_missing):
            self.dni_url = self.meta.get_field("dni_url").default
        if not self.tc_url or (not only_if_missing):
            self.tc_url = self.meta.get_field("tc_url").default
        if not self.auth_header or (not only_if_missing):
            self.auth_header = self.meta.get_field("auth_header").default
        self.cache = self.meta.get_field("cache").default

    def validate_setup(self) -> None:
        """
        Validate that all required configuration fields are set.

        Raises:
            frappe.ValidationError: If any required field is missing
        """
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

    This function retrieves the current caching configuration from the
    PERU API COM document settings. Caching helps reduce API calls and
    improves performance by storing previous responses.

    Returns:
        bool: True if caching is enabled in the configuration, False otherwise

    Example:
        >>> if use_cache():
        ...     print("Caching is enabled - will check for existing data first")
        ... else:
        ...     print("Caching disabled - will always make fresh API calls")

    Note:
        The cache setting can be configured in the PERU API COM document
        by System Managers. This function uses Frappe's cached value system
        for optimal performance.
    """
    return frappe.get_cached_value("PERU API COM", "PERU API COM", "cache")


def get_kwargs(
    endpoint: str, key: Optional[str] = None, param: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build request kwargs for API calls to PERU API COM service.

    This function constructs the necessary parameters for making HTTP requests
    to the PERU API COM service, including proper authentication headers and URL formatting.

    Args:
        endpoint: The API endpoint name (e.g., 'ruc', 'dni', 'tc', 'ruc_suc')
        key: The key value for the request (e.g., RUC number, DNI number, date)
        param: The parameter name for query-based requests (e.g., 'fecha' for TC endpoint)

    Returns:
        Dictionary containing:
        - url: Complete URL for the API endpoint
        - headers: Authentication headers including Bearer token and custom auth header
        - params: Query parameters (only when param is provided)

    Example:
        >>> kwargs = get_kwargs('ruc', '20123456789')
        >>> # Returns: {'url': 'https://api.example.com/ruc/20123456789', 'headers': {...}}

        >>> kwargs = get_kwargs('tc', '2025-01-01', 'fecha')
        >>> # Returns: {'url': 'https://api.example.com/tc', 'headers': {...}, 'params': {'fecha': '2025-01-01'}}
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
    Generic function to make API calls with caching and logging support.

    This is the core function that handles all API interactions with proper
    error handling, caching logic, and comprehensive logging. It follows
    this workflow:
    1. Check cache if enabled and requested
    2. Build request parameters with authentication
    3. Make HTTP GET request to Peru API
    4. Log successful responses for caching
    5. Handle and log any errors with user-friendly messages

    Args:
        endpoint: The API endpoint to call ('ruc', 'dni', 'tc', 'ruc_suc')
        key: The key value for the request (RUC, DNI, date, etc.)
        cache: Whether to use cached data if available (default: True)
        param: The parameter name for query-based requests (e.g., 'fecha')

    Returns:
        Dictionary containing API response data with the structure dependent
        on the endpoint called.

    Raises:
        Exception: If the API call fails, raises an exception with:
        - User-friendly error message indicating what was being searched
        - Full traceback for debugging
        - Proper error logging for monitoring

    Example:
        >>> data = _make_api_call('ruc', '20100121809', cache=True)
        >>> print(data['razon_social'])  # Company name

        >>> tc_data = _make_api_call('tc', '2025-10-17', param='fecha')
        >>> print(f"Purchase rate: {tc_data['compra']} PEN")
        >>> print(f"Source: {tc_data['fuente']}")
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

        # Make the actual HTTP GET request to PERU API COM
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
def get_rut(rut: str, cache: bool = True, sucursales: bool = False) -> Dict[str, Any]:
    """
    Get RUT information by routing to appropriate service based on number length.

    RUT (Registro Único de Tributarios) is a tax identification number that can
    be either a DNI (8 digits for individuals) or RUC (11 digits for companies).
    This function automatically determines the correct endpoint based on length.

    Args:
        rut: The RUT number (8 digits for DNI, 11 digits for RUC)
        cache: Whether to use cached data if available (default: True)
        sucursales: Whether to include branch information (default: False)

    Returns:
        Dictionary containing RUT information. Structure varies based on type:
        - DNI: Personal information (names, identification data)
        - RUC: Company information (business name, status, address, etc.)

    Example:
        >>> # For DNI (8 digits)
        >>> person_data = get_rut("70613577")
        >>> print(person_data['cliente'])  # Full name
        >>> print(person_data['nombres'])  # First names

        >>> # For RUC (11 digits)
        >>> company_data = get_rut("20100121809")
        >>> print(company_data['razon_social'])  # Company name
    """
    if len(rut) == 8:
        return get_dni(rut, cache=cache)
    else:
        return get_ruc(rut, cache=cache, sucursales=sucursales)


@frappe.whitelist()
def get_ruc(ruc: str, cache: bool = True, sucursales: bool = False) -> Dict[str, Any]:
    """
    Get RUC (company registration) information from PERU API COM service.

    RUC (Registro Único de Contribuyentes) contains company information
    including business name, tax status, address, and location details.

    Args:
        ruc: The 11-digit RUC number to look up
        cache: Whether to use cached data if available (default: True)
        sucursales: Whether to include branch/subsidiary information (default: False)

    Returns:
        Dictionary containing RUC information with keys:
        - ruc: The RUC number
        - razon_social: Company legal name
        - estado: Tax status (ACTIVO, etc.)
        - condicion: Tax condition (HABIDO, etc.)
        - direccion: Registered address
        - ubigeo: Geographic location code (6-digit)
        - departamento: Department/state name
        - provincia: Province name
        - distrito: District name
        - fecha_actualizacion: Last update timestamp
        - mensaje: Response message (usually "OK")
        - code: HTTP response code (usually "200")
        - sucursales: List of branches (only if sucursales=True)

    Example:
        >>> # Basic company information
        >>> company = get_ruc("20100121809")
        >>> print(f"{company['razon_social']} - {company['estado']}")
        >>> print(f"Address: {company['direccion']}, {company['distrito']}")

        >>> # Include branch information
        >>> company_with_branches = get_ruc("20100121809", sucursales=True)
        >>> for branch in company_with_branches.get('sucursales', []):
        ...     print(f"Branch: {branch['direccion']}")
    """
    if sucursales:
        return get_ruc_suc(ruc, cache=cache)

    return _make_api_call("ruc", key=ruc, cache=cache)


@frappe.whitelist()
def get_ruc_suc(ruc: str, cache: bool = True) -> Dict[str, Any]:
    """
    Get RUC branch/subsidiary (sucursal) information from PERU API COM service.

    This endpoint provides information about all registered branches and subsidiaries
    of a company, including their addresses and location details.

    Args:
        ruc: The 11-digit RUC number to look up branches for
        cache: Whether to use cached data if available (default: True)

    Returns:
        Dictionary containing branch information with structure:
        - ruc: The RUC number
        - razon_social: Company legal name
        - estado: Tax status (ACTIVO, etc.)
        - condicion: Tax condition (HABIDO, etc.)
        - direccion: Registered address
        - ubigeo: Geographic location code (6-digit)
        - departamento: Department/state name
        - provincia: Province name
        - distrito: District name
        - fecha_actualizacion: Last update timestamp
        - total_sucursales: Total number of branches
        - has_sucursales: Boolean indicating if company has branches
        - ultima_actualizacion_sucursales: Last update timestamp for branch data
        - sucursales: List of branch objects, each containing:
          - direccion: Branch address
          - ubigeo: Geographic location code (6-digit)
          - departamento: Department/state name
          - provincia: Province name
          - distrito: District name
          - fecha_actualizacion: Last update timestamp for this branch
        - mensaje: Response message (usually "OK")
        - code: HTTP response code (usually "200")

    Example:
        >>> branches = get_ruc_suc("20100121809")
        >>> print(f"Company: {branches['razon_social']}")
        >>> print(f"Total branches: {branches['total_sucursales']}")
        >>> for branch in branches.get('sucursales', []):
        ...     print(f"Branch: {branch['direccion']}")
        ...     print(f"Location: {branch['distrito']}, {branch['provincia']}")
    """
    return _make_api_call("ruc_suc", key=ruc, cache=cache)


@frappe.whitelist()
def get_dni(dni: str, cache: bool = True) -> Dict[str, Any]:
    """
    Get DNI (national ID) information from PERU API COM service.

    DNI (Documento Nacional de Identidad) contains personal information
    for Peruvian citizens including names and basic identification data.

    Args:
        dni: The 8-digit DNI number to look up
        cache: Whether to use cached data if available (default: True)

    Returns:
        Dictionary containing personal information with keys:
        - dni: The DNI number
        - cliente: Full name (complete name string)
        - nombres: First and middle names
        - apellido_paterno: Paternal surname
        - apellido_materno: Maternal surname
        - mensaje: Response message (usually "OK")
        - code: HTTP response code (usually "200")

    Example:
        >>> person = get_dni("70613577")
        >>> print(f"Full name: {person['cliente']}")
        >>> print(f"First names: {person['nombres']}")
        >>> print(f"Surnames: {person['apellido_paterno']} {person['apellido_materno']}")
        >>> print(f"DNI: {person['dni']}")

    Note:
        The API returns basic identification information. Additional fields
        like address or birth date are not included in this service.
    """
    return _make_api_call("dni", key=dni, cache=cache)


@frappe.whitelist()
def get_tc(
    date: Optional[Union[str, date]] = None, cache: bool = True
) -> Dict[str, Any]:
    """
    Get exchange rate (tipo de cambio) information from PERU API COM service.

    Retrieves USD to PEN exchange rates for a specific date. Rates include
    both purchase and sale prices from official sources.

    Args:
        date: The date to get exchange rate for. Accepts:
              - datetime.date object
              - String in YYYY-MM-DD format
              - None (defaults to current date)
        cache: Whether to use cached data if available (default: True)

    Returns:
        Dictionary containing exchange rate information:
        - fecha: The date for the exchange rate (YYYY-MM-DD format)
        - compra: Purchase rate (buying USD with PEN)
        - venta: Sale rate (selling USD for PEN)
        - moneda: Currency code (always "USD")
        - fuente: Data source (e.g., "SUNAT")
        - updated_at: Last update timestamp
        - mensaje: Response message (usually "OK")
        - code: HTTP response code (usually "200")

    Example:
        >>> # Get today's exchange rate
        >>> today_tc = get_tc()
        >>> print(f"USD Purchase: {today_tc['compra']} PEN")
        >>> print(f"USD Sale: {today_tc['venta']} PEN")
        >>> print(f"Source: {today_tc['fuente']}")

        >>> # Get specific date exchange rate
        >>> historical_tc = get_tc("2025-10-17")
        >>> print(f"Rate on {historical_tc['fecha']}: {historical_tc['venta']}")
        >>> print(f"Updated: {historical_tc['updated_at']}")

    Note:
        Exchange rates may not be available for all dates depending on
        the data source and API service availability.
    """
    date = getdate(date)
    date = format_date(date, "yyyy-mm-dd")

    return _make_api_call("tc", key=date, param="fecha", cache=cache)


@frappe.whitelist()
def restore_defaults(only_if_missing: bool = False) -> None:
    """
    Restore default configuration values for PERU API COM settings.

    This function resets the API configuration to default values, useful for
    initial setup or when configuration becomes corrupted. Only System Managers
    can execute this function for security reasons.

    Args:
        only_if_missing: If True, only restore fields that are currently empty.
                        If False, restore all fields to defaults regardless of current values.

    Raises:
        frappe.PermissionError: If the current user is not a System Manager

    Example:
        >>> # Restore only empty fields
        >>> restore_defaults(only_if_missing=True)

        >>> # Reset all configuration to defaults
        >>> restore_defaults(only_if_missing=False)

    Note:
        This function saves the document after restoring defaults, so changes
        are immediately persisted to the database.
    """
    frappe.only_for("System Manager")

    doc = frappe.get_doc("PERU API COM")

    doc.restore_defaults(only_if_missing)

    doc.save()


@frappe.whitelist()
def get_default_settings() -> Dict[str, Any]:
    """
    Get default configuration settings for PERU API COM without saving changes.

    This function retrieves a copy of the PERU API COM configuration with all
    fields set to their default values. Useful for comparing current settings
    against defaults or for configuration management. Only System Managers
    can access this function.

    Returns:
        Dictionary containing all default configuration values including:
        - website_url: Base URL for the API service
        - ruc_url: Endpoint URL for RUC queries
        - ruc_suc_url: Endpoint URL for RUC branch queries
        - dni_url: Endpoint URL for DNI queries
        - tc_url: Endpoint URL for exchange rate queries
        - auth_header: Custom authorization header name
        - cache: Default caching behavior setting

    Raises:
        frappe.PermissionError: If the current user is not a System Manager

    Example:
        >>> defaults = get_default_settings()
        >>> print(f"Default API URL: {defaults['website_url']}")
        >>> print(f"Caching enabled by default: {defaults['cache']}")

    Note:
        This function does NOT save any changes to the database. It only
        returns the default values for inspection or comparison purposes.
    """
    frappe.only_for("System Manager")

    doc = frappe.get_doc("PERU API COM")
    doc.restore_defaults()

    return doc.as_dict()


@frappe.whitelist()
def create_customer(rut: str) -> Dict[str, Any]:
    """
    Create or sync a customer in the system using a provided tax ID.

    Args:
        rut (str): The customer's tax ID (RUC/DNI).

    Returns:
        dict: Customer details as a dictionary.
    """
    # Check if customer already exists
    customer_exists = frappe.db.exists("Customer", {"tax_id": rut})

    if customer_exists:
        # Fetch existing customer and sync with Sunat
        customer = frappe.get_doc("Customer", customer_exists)
        sync_customer_with_sunat(customer)
        return customer.as_dict()

    else:
        # Create a new customer if not existing
        customer = get_customer(rut)
        customer.save()
        return customer.as_dict()


@frappe.whitelist()
def get_customer(rut: str, customer=None):
    """
    Fetch and update customer details with data fetched from API.

    Args:
        rut (str): The customer's tax ID (RUC/DNI).
        customer (Document, optional): Existing customer document to update.

    Returns:
        Document: Updated customer document.
    """
    # Fetch data of the customer
    result = get_rut(rut)

    # Create a new customer document if not provided
    if not customer:
        customer = frappe.get_doc({"doctype": "Customer"})

    # Update customer name
    if "razon_social" in result:
        customer.set("customer_name", result["razon_social"])
    elif "cliente" in result:
        customer.set("customer_name", result["cliente"])

    # Set customer tax ID
    customer.set("tax_id", rut)

    # Update address details if available
    if (
        "direccion" in result
        and result["direccion"]
        and "distrito" in result
        and result["distrito"]
        and result["distrito"] != "-"
        and "provincia" in result
        and result["provincia"]
        and result["provincia"] != "-"
        and "departamento" in result
        and result["departamento"]
        and result["departamento"] != "-"
    ):
        customer.set(
            "quick_primary_address",
            {
                "address_line1": result["direccion"],
                "county": result["distrito"],
                "city": result["provincia"],
                "state": result["departamento"],
                "country": "Peru",
            },
        )

    return customer


def sync_customer_with_sunat(customer):
    """
    Sync customer details with Sunat API, including address creation if not existing.

    Args:
        customer (Document): Customer document to sync.
    """

    # Fetch and update customer details
    get_customer(customer.tax_id, customer)
    customer.save()

    # Return if address is not set
    if not customer.get("address_line1", ""):
        return

    # Create and validate new address
    new_address = make_address(customer, insert=0)
    new_address.validate_address_parts()

    # Check if a similar address already exists
    customer_addresses = frappe.db.get_all(
        "Address",
        pluck="name",
        filters=[["Dynamic Link", "link_name", "=", customer.name]],
    )
    for address_name in customer_addresses:
        address: Address = frappe.get_doc("Address", address_name)
        if address.get_display() == new_address.get_display():
            return

    # Insert new address and update customer primary address details
    new_address.insert()
    customer.db_set(
        {
            "customer_primary_address": new_address.name,
            "primary_address": new_address.get_display(),
        }
    )


@frappe.whitelist()
def update_currency_exchange(
    date: Optional[Union[str, date]] = None, cache: bool = False
) -> Dict[str, Any]:
    """
    Update currency exchange rates in the system using PERU API COM service.

    This function fetches exchange rate data from PERU API COM and creates or updates
    Currency Exchange records in the system for both USD->PEN and PEN->USD conversions.

    Args:
        date: The date for which to update exchange rates. If None, uses current date.
        cache: Whether to use cached data if available (default: False for fresh rates).

    Returns:
        Dictionary containing the exchange rate data that was processed.

    Raises:
        Exception: If API call fails or exchange rate data is invalid.

    Example:
        >>> # Update today's rates
        >>> tc_data = update_currency_exchange()
        >>> print(f"Updated rates for {tc_data['fecha']}")

        >>> # Update specific date rates
        >>> tc_data = update_currency_exchange("2025-01-15")
    """
    tc_data = get_tc(date=date, cache=cache)
    date = getdate(tc_data["fecha"])

    # Use 'venta' (sale rate) for USD to PEN conversion
    from_usd_to_pen = float(tc_data["venta"])

    # Calculate inverse rate using 'compra' (purchase rate) with zero division protection
    compra_rate = float(tc_data["compra"])
    from_pen_to_usd = round(1 / compra_rate, 6) if compra_rate != 0 else 0

    # Create/update exchange rate records
    if from_usd_to_pen > 0:
        set_currency_exchange(
            date=date,
            from_currency="USD",
            to_currency="PEN",
            exchange_rate=from_usd_to_pen,
        )

    if from_pen_to_usd > 0:
        set_currency_exchange(
            date=date,
            from_currency="PEN",
            to_currency="USD",
            exchange_rate=from_pen_to_usd,
        )

    return tc_data


@frappe.whitelist()
def set_currency_exchange(
    date: Union[str, date], from_currency: str, to_currency: str, exchange_rate: float
) -> CurrencyExchange:
    """
    Create or update a currency exchange rate record for a specific date and currency pair.

    Args:
        date: The date for the exchange rate
        from_currency: The source currency code (e.g., 'USD')
        to_currency: The target currency code (e.g., 'PEN')
        exchange_rate: The exchange rate value

    Returns:
        The created or updated CurrencyExchange document
    """
    existing_name = frappe.db.get_value(
        "Currency Exchange",
        {
            "date": date,
            "from_currency": from_currency,
            "to_currency": to_currency,
        },
    )

    if existing_name:
        doc = frappe.get_doc("Currency Exchange", existing_name)
        # Only update if rate has changed to avoid unnecessary saves
        if (
            abs(float(doc.exchange_rate) - exchange_rate) > 0.000001
        ):  # Use epsilon comparison for floats
            doc.exchange_rate = exchange_rate
            doc.save()
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Currency Exchange",
                "date": date,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": exchange_rate,
            }
        )
        doc.insert()

    return doc


def autoupdate_currency_exchange():
    """
    Automatically update currency exchange rates if auto-update is enabled.

    This function checks the PERU API COM configuration to see if automatic
    currency exchange updates are enabled, and if so, updates the rates using
    the current date.

    This function is called by scheduled jobs to ensure
    exchange rates are kept current without manual intervention.

    Example:
        >>> # Called by scheduler
        >>> autoupdate_currency_exchange()
    """
    if frappe.get_cached_value(
        "PERU API COM", "PERU API COM", "auto_update_currency_exchange"
    ):
        update_currency_exchange()
