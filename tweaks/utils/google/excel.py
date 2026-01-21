# Copyright (c) 2026, and contributors
# For license information, please see license.txt

import io

import frappe
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


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
