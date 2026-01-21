# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleServiceAccount(Document):
    def validate(self):
        """Process json_key_input if provided and handle default flag"""
        if self.json_key_input:
            try:
                # Validate that it's proper JSON and extract client_email
                key_dict = json.loads(self.json_key_input)
                # Extract client_email
                self.client_email = key_dict.get("client_email", "")
                # Store in password field
                self.json_key = self.json_key_input
                # Clear the input field
                self.json_key_input = None
            except json.JSONDecodeError as e:
                frappe.throw(f"Invalid JSON format: {str(e)}")

        # Handle default flag - ensure only one default exists
        if self.default:
            # Unset default on all other Google Service Accounts
            other_accounts = frappe.get_all(
                "Google Service Account",
                filters={"name": ["!=", self.name], "default": 1},
                pluck="name",
            )
            for account_name in other_accounts:
                frappe.db.set_value(
                    "Google Service Account", account_name, "default", 0
                )

    def on_trash(self):
        """If deleting the default account, set another one as default"""
        if self.default:
            # Find another account to set as default
            other_account = frappe.db.get_value(
                "Google Service Account", {"name": ["!=", self.name]}, "name"
            )
            if other_account:
                frappe.db.set_value(
                    "Google Service Account", other_account, "default", 1
                )

    def get_credentials(self):
        """Get Google credentials from the stored JSON key"""
        try:
            json_key = self.get_password("json_key")
            key_dict = json.loads(json_key)
            SCOPES = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/spreadsheets",
            ]
            credentials = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES
            )
            return credentials
        except json.JSONDecodeError as e:
            frappe.throw(f"Invalid JSON key format: {str(e)}")
        except Exception as e:
            frappe.throw(f"Error creating credentials: {str(e)}")

    def get_sheets_service(self, spreadsheet_id):
        """
        Create a GoogleSheetsService for this service account

        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet

        Returns:
            GoogleSheetsService: Service object for the spreadsheet
        """
        credentials = self.get_credentials()
        return GoogleSheetsService(spreadsheet_id, credentials)


class GoogleSheetsService:
    """Service for interacting with a specific Google Spreadsheet using a service account"""

    def __init__(self, spreadsheet_id, credentials):
        """
        Initialize Google Sheets service for a spreadsheet

        Args:
            spreadsheet_id (str): The ID of the Google Spreadsheet
            credentials: Google service account credentials
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials = credentials
        self.service = build("sheets", "v4", credentials=credentials)

    def get_sheet_titles(self):
        """
        Get all sheet titles from the spreadsheet

        Returns:
            list: List of sheet titles
        """
        try:
            spreadsheet = (
                self.service.spreadsheets()
                .get(spreadsheetId=self.spreadsheet_id)
                .execute()
            )
            sheets_list = spreadsheet.get("sheets", [])
            return [sheet["properties"]["title"] for sheet in sheets_list]
        except Exception as e:
            frappe.log_error(f"Error fetching sheet titles: {str(e)}")
            frappe.throw(f"Failed to fetch sheet titles: {str(e)}")

    def get_values(self, range_name):
        """
        Get values from a specific range in the spreadsheet

        Args:
            range_name (str): The A1 notation of the range to retrieve (e.g., "Sheet1!A1:C10" or "A1:C10")

        Returns:
            list: List of lists containing the cell values
        """
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_name)
                .execute()
            )
            values = result.get("values", [])
            return values
        except Exception as e:
            frappe.log_error(f"Error fetching values: {str(e)}")
            frappe.throw(f"Failed to fetch values: {str(e)}")

    def get_rows(
        self,
        range_name,
        first_row_as_headers=False,
        columns=None,
    ):
        """
        Get rows from a specific range as dictionaries

        Args:
            range_name (str): The A1 notation of the range to retrieve
            first_row_as_headers (bool): If True, use first row as keys for dictionaries
            columns (list): Array of column names to use as keys instead of first row

        Returns:
            list: List of dictionaries with column names as keys
        """
        values = self.get_values(range_name)

        if not values:
            return []

        # Determine headers
        headers = None
        data_start_index = 0

        if columns:
            # Use provided columns
            headers = columns
            # If first_row_as_headers is also True, skip the first row
            if first_row_as_headers:
                data_start_index = 1
        elif first_row_as_headers:
            # Use first row as headers
            if len(values) > 0:
                headers = values[0]
                data_start_index = 1
            else:
                return []
        else:
            # No headers specified, return empty list or raw values
            return values

        # Deduplicate headers by affixing numbers incrementally
        deduplicated_headers = []
        header_count = {}
        for header in headers:
            if header in header_count:
                header_count[header] += 1
                deduplicated_headers.append(f"{header} {header_count[header]}")
            else:
                header_count[header] = 1
                deduplicated_headers.append(header)

        # Convert rows to dictionaries
        rows = []
        for row in values[data_start_index:]:
            # Pad row with empty strings if shorter than headers
            padded_row = (
                row + [""] * (len(deduplicated_headers) - len(row))
                if len(row) < len(deduplicated_headers)
                else row
            )
            # Create dictionary with headers as keys
            row_dict = {
                deduplicated_headers[i]: padded_row[i] if i < len(padded_row) else ""
                for i in range(len(deduplicated_headers))
            }
            rows.append(row_dict)

        return rows


@frappe.whitelist()
def get_sheet_titles(spreadsheet_id, serviceaccount=None):
    """
    Whitelisted method to get sheet titles

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet
        serviceaccount (str, optional): Name of the Google Service Account document.
                                        If not provided, uses the default account.

    Returns:
        list: List of sheet titles
    """
    if not serviceaccount:
        doc = get_default_account()
    else:
        doc = frappe.get_doc("Google Service Account", serviceaccount)

    doc.check_permission("read")
    service = doc.get_sheets_service(spreadsheet_id)
    return service.get_sheet_titles()


@frappe.whitelist()
def get_values(spreadsheet_id, range_name, serviceaccount=None):
    """
    Whitelisted method to get values from a spreadsheet

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet
        range_name (str): The A1 notation of the range to retrieve
        serviceaccount (str, optional): Name of the Google Service Account document.
                                        If not provided, uses the default account.

    Returns:
        list: List of lists containing the cell values
    """
    if not serviceaccount:
        doc = get_default_account()
    else:
        doc = frappe.get_doc("Google Service Account", serviceaccount)

    doc.check_permission("read")
    service = doc.get_sheets_service(spreadsheet_id)
    return service.get_values(range_name)


@frappe.whitelist()
def get_rows(
    spreadsheet_id,
    range_name,
    first_row_as_headers=False,
    columns=None,
    serviceaccount=None,
):
    """
    Whitelisted method to get rows from a spreadsheet as dictionaries

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet
        range_name (str): The A1 notation of the range to retrieve
        first_row_as_headers (bool): If True, use first row as keys for dictionaries
        columns (list): Array of column names to use as keys instead of first row
        serviceaccount (str, optional): Name of the Google Service Account document.
                                        If not provided, uses the default account.

    Returns:
        list: List of dictionaries with column names as keys
    """
    if not serviceaccount:
        doc = get_default_account()
    else:
        doc = frappe.get_doc("Google Service Account", serviceaccount)

    doc.check_permission("read")

    # Convert string to boolean if needed
    if isinstance(first_row_as_headers, str):
        first_row_as_headers = first_row_as_headers.lower() in ("true", "1", "yes")

    # Parse columns if it's a JSON string
    if isinstance(columns, str):
        try:
            columns = json.loads(columns)
        except json.JSONDecodeError:
            columns = None

    service = doc.get_sheets_service(spreadsheet_id)
    return service.get_rows(range_name, first_row_as_headers, columns)


def get_default_account():
    """
    Get the default Google Service Account

    Returns:
        GoogleServiceAccount: The default account document
    """
    default_account = frappe.db.get_value(
        "Google Service Account", {"default": 1}, "name"
    )
    if not default_account:
        # If no default, get the first one
        default_account = frappe.db.get_value("Google Service Account", {}, "name")

    if not default_account:
        frappe.throw("No Google Service Account found. Please create one first.")

    return frappe.get_doc("Google Service Account", default_account)
