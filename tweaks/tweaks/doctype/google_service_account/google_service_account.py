# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from google.oauth2 import service_account

from tweaks.utils.google import GoogleDriveExcelService, GoogleSheetsService


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
                "https://www.googleapis.com/auth/drive.readonly",
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

    def get_excel_service(self, file_id):
        """
        Create a GoogleDriveExcelService for this service account

        Args:
            file_id (str): The Google Drive file ID of the Excel file

        Returns:
            GoogleDriveExcelService: Service object for the Excel file
        """
        credentials = self.get_credentials()
        return GoogleDriveExcelService(file_id, credentials)


@frappe.whitelist()
def get_sheet_titles(spreadsheet_id, serviceaccount=None, file_type="sheets"):
    """
    Whitelisted method to get sheet titles

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet or Excel file
        serviceaccount (str, optional): Name of the Google Service Account document.
                                        If not provided, uses the default account.
        file_type (str, optional): Type of file - "sheets" or "excel". Defaults to "sheets".

    Returns:
        list: List of sheet titles
    """
    if not serviceaccount:
        doc = get_default_account()
    else:
        doc = frappe.get_doc("Google Service Account", serviceaccount)

    doc.check_permission("read")

    if file_type == "excel":
        service = doc.get_excel_service(spreadsheet_id)
    else:
        service = doc.get_sheets_service(spreadsheet_id)

    return service.get_sheet_titles()


@frappe.whitelist()
def get_values(
    spreadsheet_id, sheet=None, cell_range=None, serviceaccount=None, file_type="sheets"
):
    """
    Whitelisted method to get values from a spreadsheet

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet or Excel file
        sheet (str, optional): The name of the sheet. If not provided, uses first sheet.
        cell_range (str, optional): The A1 notation of the range (e.g., "A1:C10"). If not provided, gets all data.
        serviceaccount (str, optional): Name of the Google Service Account document.
                                        If not provided, uses the default account.
        file_type (str, optional): Type of file - "sheets" or "excel". Defaults to "sheets".

    Returns:
        list: List of lists containing the cell values
    """
    if not serviceaccount:
        doc = get_default_account()
    else:
        doc = frappe.get_doc("Google Service Account", serviceaccount)

    doc.check_permission("read")

    if file_type == "excel":
        service = doc.get_excel_service(spreadsheet_id)
    else:
        service = doc.get_sheets_service(spreadsheet_id)

    return service.get_values(sheet=sheet, cell_range=cell_range)


@frappe.whitelist()
def get_rows(
    spreadsheet_id,
    sheet=None,
    cell_range=None,
    first_row_as_headers=False,
    columns=None,
    serviceaccount=None,
    file_type="sheets",
):
    """
    Whitelisted method to get rows from a spreadsheet as dictionaries

    Args:
        spreadsheet_id (str): The ID of the Google Spreadsheet or Excel file
        sheet (str, optional): The name of the sheet. If not provided, uses first sheet.
        cell_range (str, optional): The A1 notation of the range (e.g., "A1:C10"). If not provided, gets all data.
        first_row_as_headers (bool): If True, use first row as keys for dictionaries
        columns (list): Array of column names to use as keys instead of first row
        serviceaccount (str, optional): Name of the Google Service Account document.
                                        If not provided, uses the default account.
        file_type (str, optional): Type of file - "sheets" or "excel". Defaults to "sheets".

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

    if file_type == "excel":
        service = doc.get_excel_service(spreadsheet_id)
    else:
        service = doc.get_sheets_service(spreadsheet_id)

    return service.get_rows(
        sheet=sheet,
        cell_range=cell_range,
        first_row_as_headers=first_row_as_headers,
        columns=columns,
    )


def get_default_account() -> GoogleServiceAccount:
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
