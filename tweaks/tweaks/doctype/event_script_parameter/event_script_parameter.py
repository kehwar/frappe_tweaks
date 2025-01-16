# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class EventScriptParameter(Document):

    def before_validate(self):

        doctype = self.document_type
        docname = self.document_name
        fields = self.field or "name"
        if "," in fields:
            fields = [field.strip() for field in fields.split(",")]

        json_value = json.dumps(frappe.db.get_value(doctype, docname, fields))
        self.value = json_value[:140]
