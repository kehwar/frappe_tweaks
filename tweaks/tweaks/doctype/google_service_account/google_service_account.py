# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import io
import json

import frappe
import pandas as pd
from frappe.model.document import Document
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


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


class GoogleSheetsService:
    """Service for interacting with Google Sheets using the Sheets API v4"""

    def __init__(self, spreadsheet_id, credentials):
        """
        Initialize Google Sheets service

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

    def get_values(self, sheet=None, cell_range=None):
        """
        Get values from a specific range in the spreadsheet

        Args:
            sheet (str, optional): The name of the sheet. If not provided, uses first sheet.
            cell_range (str, optional): The A1 notation of the range (e.g., "A1:C10"). If not provided, gets all data.

        Returns:
            list: List of lists containing the cell values
        """
        try:
            # Determine the sheet to use
            if sheet is None:
                # Get first sheet
                sheet_titles = self.get_sheet_titles()
                if not sheet_titles:
                    frappe.throw("Spreadsheet has no sheets")
                sheet = sheet_titles[0]

            # Build the range_name
            if cell_range:
                range_name = f"'{sheet}'!{cell_range}"
            else:
                range_name = f"'{sheet}'"

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
        sheet=None,
        cell_range=None,
        first_row_as_headers=False,
        columns=None,
    ):
        """
        Get rows from a specific range as dictionaries

        Args:
            sheet (str, optional): The name of the sheet. If not provided, uses first sheet.
            cell_range (str, optional): The A1 notation of the range (e.g., "A1:C10"). If not provided, gets all data.
            first_row_as_headers (bool): If True, use first row as keys for dictionaries
            columns (list): Array of column names to use as keys instead of first row

        Returns:
            list: List of dictionaries with column names as keys
        """
        values = self.get_values(sheet=sheet, cell_range=cell_range)

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


class GoogleDriveExcelService:
    """Service for reading Microsoft Excel files from Google Drive"""

    def __init__(self, spreadsheet_id, credentials):
        """
        Initialize Excel service for a file in Google Drive

        Args:
            spreadsheet_id (str): The Google Drive file ID
            credentials: Google service account credentials
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials = credentials
        self.drive_service = build("drive", "v3", credentials=credentials)
        self._excel_file = None  # Cache the downloaded Excel file

    def _download_excel(self):
        """Download Excel file from Google Drive and cache it"""
        if self._excel_file is not None:
            return self._excel_file

        try:
            request = self.drive_service.files().get_media(fileId=self.spreadsheet_id)
            file_bytes = io.BytesIO()
            downloader = MediaIoBaseDownload(file_bytes, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()

            file_bytes.seek(0)
            # Read Excel file with all sheets
            self._excel_file = pd.ExcelFile(file_bytes)
            return self._excel_file
        except Exception as e:
            frappe.log_error(f"Error downloading Excel file: {str(e)}")
            frappe.throw(f"Failed to download Excel file: {str(e)}")

    def _parse_range(self, range_name):
        """
        Parse A1 notation range into sheet name and cell range

        Args:
            range_name (str): Range in format "Sheet1!A1:C10", "A1:C10", or "Sheet1"

        Returns:
            tuple: (sheet_name, cell_range) e.g., ("Sheet1", "A1:C10") or ("Sheet1", None)
        """
        import re

        if "!" in range_name:
            parts = range_name.split("!", 1)
            sheet_name = parts[0].strip("'\"")
            cell_range = parts[1] if len(parts) > 1 and parts[1] else None
        else:
            # Check if it looks like a cell range (A1 notation)
            # Cell pattern: ONLY capital letters (A-Z, AA-ZZ, etc.) followed by ONLY digits
            # This ensures "Sheet1" is NOT matched (has lowercase), but "A1" or "AA100" is
            cell_pattern = r"^[A-Z]+\d+(?::[A-Z]+\d+)?$"
            if re.match(cell_pattern, range_name):
                # It's a cell range like "A1" or "A1:C10", use first sheet
                sheet_name = 0
                cell_range = range_name
            else:
                # It's a sheet name (like "Sheet1", "My Data", etc.)
                sheet_name = range_name.strip("'\"")
                cell_range = None

        return sheet_name, cell_range

    def _parse_cell_range(self, cell_range):
        """
        Parse cell range like "A1:C10" into start and end coordinates

        Args:
            cell_range (str): Cell range in A1 notation

        Returns:
            tuple: (start_cell, end_cell) e.g., ("A1", "C10")
        """
        if ":" in cell_range:
            parts = cell_range.split(":")
            return parts[0], parts[1]
        else:
            # Single cell
            return cell_range, cell_range

    def _column_letter_to_index(self, col_letter):
        """Convert column letter(s) to 0-based index (A=0, B=1, ..., Z=25, AA=26, etc.)"""
        index = 0
        for char in col_letter.upper():
            index = index * 26 + (ord(char) - ord("A") + 1)
        return index - 1

    def _parse_cell_reference(self, cell_ref):
        """
        Parse cell reference like "A1" into column index and row index

        Args:
            cell_ref (str): Cell reference like "A1", "B10", "AA5"

        Returns:
            tuple: (col_index, row_index) - both 0-based
        """
        import re

        match = re.match(r"([A-Z]+)(\d+)", cell_ref.upper())
        if not match:
            raise ValueError(f"Invalid cell reference: {cell_ref}")

        col_letter, row_num = match.groups()
        col_index = self._column_letter_to_index(col_letter)
        row_index = int(row_num) - 1  # Convert to 0-based

        return col_index, row_index

    def _slice_dataframe(self, df, start_cell, end_cell):
        """
        Slice a dataframe based on cell range

        Args:
            df: pandas DataFrame
            start_cell (str): Start cell like "A1"
            end_cell (str): End cell like "C10"

        Returns:
            DataFrame: Sliced dataframe
        """
        start_col, start_row = self._parse_cell_reference(start_cell)
        end_col, end_row = self._parse_cell_reference(end_cell)

        # Slice the dataframe
        sliced = df.iloc[start_row : end_row + 1, start_col : end_col + 1]
        return sliced

    def get_sheet_titles(self):
        """
        Get all sheet names from the Excel file

        Returns:
            list: List of sheet names
        """
        try:
            excel_file = self._download_excel()
            return excel_file.sheet_names
        except Exception as e:
            frappe.log_error(f"Error fetching sheet titles: {str(e)}")
            frappe.throw(f"Failed to fetch sheet titles: {str(e)}")

    def get_values(self, sheet=None, cell_range=None):
        """
        Get values from a specific range in the Excel file

        Args:
            sheet (str, optional): The name of the sheet. If not provided, uses first sheet (index 0).
            cell_range (str, optional): The A1 notation of the cell range (e.g., "A1:C10"). If not provided, gets all data.

        Returns:
            list: List of lists containing the cell values
        """
        try:
            excel_file = self._download_excel()

            # Determine the sheet to use
            if sheet is None:
                # Use first sheet (index 0)
                sheet_name = 0
            else:
                sheet_name = sheet

            # Read the specific sheet
            df = pd.read_excel(
                excel_file, sheet_name=sheet_name, header=None, dtype=str
            )

            # Parse cell range if specified
            if cell_range:
                start_cell, end_cell = self._parse_cell_range(cell_range)
                df = self._slice_dataframe(df, start_cell, end_cell)

            # Convert to list of lists, replacing NaN with empty strings
            values = df.fillna("").values.tolist()
            return values
        except Exception as e:
            frappe.log_error(f"Error fetching values: {str(e)}")
            frappe.throw(f"Failed to fetch values: {str(e)}")

    def get_rows(
        self,
        sheet=None,
        cell_range=None,
        first_row_as_headers=False,
        columns=None,
    ):
        """
        Get rows from a specific range as dictionaries

        Args:
            sheet (str, optional): The name of the sheet. If not provided, uses first sheet (index 0).
            cell_range (str, optional): The A1 notation of the cell range (e.g., "A1:C10"). If not provided, gets all data.
            first_row_as_headers (bool): If True, use first row as keys for dictionaries
            columns (list): Array of column names to use as keys instead of first row

        Returns:
            list: List of dictionaries with column names as keys
        """
        values = self.get_values(sheet=sheet, cell_range=cell_range)

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
