# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

import json
import re

import frappe
from frappe.model.document import Document


class GoogleSpreadsheet(Document):
    def validate(self):
        self.autocomplete_url_and_spreadsheet_id()

    def autocomplete_url_and_spreadsheet_id(self):
        """Auto-complete URL from spreadsheet_id or extract spreadsheet_id from URL"""
        # Pattern to extract spreadsheet ID from Google Sheets URL
        # Handles URLs like: https://docs.google.com/spreadsheets/d/{id}/edit?gid=...#gid=...
        spreadsheet_pattern = (
            r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)(?:/|$|\?)"
        )

        # If URL is provided but spreadsheet_id is not
        if self.url and not self.spreadsheet_id:
            match = re.search(spreadsheet_pattern, self.url)
            if match:
                self.spreadsheet_id = match.group(1)

        # If spreadsheet_id is provided
        if self.spreadsheet_id:
            self.url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

    def get_values(self, sheet=None, cell_range=None, serviceaccount=None):
        """
        Get values from the spreadsheet

        Args:
            sheet (str, optional): The name of the sheet. If not provided, uses sheet_title from doc or first sheet.
            cell_range (str, optional): The A1 notation of the range (e.g., "A1:C10"). If not provided, gets all data.
            serviceaccount (str, optional): Name of the Google Service Account document.
                                            If not provided, uses the default account.

        Returns:
            list: List of lists containing the cell values
        """
        from tweaks.tweaks.doctype.google_service_account.google_service_account import (
            get_values,
        )

        # Use sheet_title from the document if sheet is not provided
        if sheet is None and self.sheet_title:
            sheet = self.sheet_title

        return get_values(
            spreadsheet_id=self.spreadsheet_id,
            sheet=sheet,
            cell_range=cell_range,
            serviceaccount=serviceaccount,
            file_type=self.type.lower() or "sheets",
        )

    def get_rows(
        self,
        sheet=None,
        cell_range=None,
        first_row_as_headers=False,
        columns=None,
        serviceaccount=None,
    ):
        """
        Get rows from the spreadsheet as dictionaries

        Args:
            sheet (str, optional): The name of the sheet. If not provided, uses sheet_title from doc or first sheet.
            cell_range (str, optional): The A1 notation of the range (e.g., "A1:C10"). If not provided, gets all data.
            first_row_as_headers (bool): If True, use first row as keys for dictionaries
            columns (list): Array of column names to use as keys instead of first row
            serviceaccount (str, optional): Name of the Google Service Account document.
                                            If not provided, uses the default account.

        Returns:
            list: List of dictionaries with column names as keys
        """
        from tweaks.tweaks.doctype.google_service_account.google_service_account import (
            get_rows,
        )

        # Use sheet_title from the document if sheet is not provided
        if sheet is None and self.sheet_title:
            sheet = self.sheet_title

        return get_rows(
            spreadsheet_id=self.spreadsheet_id,
            sheet=sheet,
            cell_range=cell_range,
            first_row_as_headers=first_row_as_headers,
            columns=columns,
            serviceaccount=serviceaccount,
            file_type=self.type.lower() or "sheets",
        )
