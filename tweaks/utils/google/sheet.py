# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import frappe
from googleapiclient.discovery import build


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
