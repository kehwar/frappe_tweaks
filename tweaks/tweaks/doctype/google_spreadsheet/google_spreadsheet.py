# Copyright (c) 2026, Erick W.R. and contributors
# For license information, please see license.txt

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
