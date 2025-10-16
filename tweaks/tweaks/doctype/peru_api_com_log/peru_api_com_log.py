# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.log_settings.log_settings import LogType
from frappe.query_builder.functions import Now
from frappe.query_builder import Interval
import json


class PERUAPICOMLog(Document, LogType):
	
	@staticmethod
	def clear_old_logs(days=30):
		table = frappe.qb.DocType("PERU API COM Log")
		frappe.db.delete(table, filters=(table.modified < (Now() - Interval(days=days))))

def get_data_from_log(endpoint, key):

	data = frappe.db.get_value("PERU API COM Log", filters={"endpoint": endpoint, "key": key, "status": "Success"}, fieldname="data", order_by="creation desc")

	if data:
		return json.loads(data)

def log_api_call(endpoint, key, data=None, error=None):
	log = frappe.new_doc("PERU API COM Log")
	log.update({
		"endpoint": endpoint,
		"key": key,
		"status": "Success" if data else "Error",
		"data": json.dumps(data) if data else None,
		"error": error,
	})
	log.insert(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist()
def clear_api_logs():
	"""Flush all Error Logs"""
	frappe.only_for("System Manager")
	frappe.db.truncate("PERU API COM Log")