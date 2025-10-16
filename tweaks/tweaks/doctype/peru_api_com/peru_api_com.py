# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.integrations.utils import make_get_request
from frappe.utils import getdate, format_date
from tweaks.tweaks.doctype.peru_api_com_log.peru_api_com_log import get_data_from_log, log_api_call
from requests.exceptions import HTTPError

class PERUAPICOM(Document):

	def get_rut(self, rut, cache=True):
		return get_rut(rut, cache)

	def get_ruc(self, ruc, cache=True):
		return get_ruc(ruc, cache)

	def get_dni(self, dni, cache=True):
		return get_dni(dni, cache)

	def get_tc(self, date=None, cache=True):
		return get_tc(date, cache)

def use_cache():
	return frappe.get_cached_value("PERU API COM", "PERU API COM", "cache")

def get_kwargs(endpoint, key=None, param=None) -> dict:

	doc = frappe.get_cached_doc("PERU API COM")
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


def get_rut(rut, cache=True):

	if len(rut) == 8:
		return get_dni(rut, cache)
	else:
		return get_ruc(rut, cache)

def _make_api_call(endpoint, key=None, cache=True, param=None):
	"""Generic function to make API calls with caching and logging."""
	try:
		if cache and use_cache():
			data = get_data_from_log(endpoint, key)
			if data:
				return data

		kwargs = get_kwargs(endpoint, key, param)
		
		data = make_get_request(**kwargs)

		if use_cache():
			log_api_call(endpoint, key, data=data)
		return data
	except Exception as e:
		reason = ""
		if isinstance(e, HTTPError) and e.response is not None and e.response.reason:
			reason = e.response.reason
		else:
			reason = str(e)
		log_api_call(endpoint, key, error=reason)
		frappe.throw(reason, exc=e, title=f"Error al buscar {endpoint.upper()}: {key}")


def get_ruc(ruc, cache=True):
	return _make_api_call("ruc", key=ruc, cache=cache)


def get_dni(dni, cache=True):
	return _make_api_call("dni", key=dni, cache=cache)


def get_tc(date=None, cache=True):
	date = getdate(date)
	date = format_date(date, "yyyy-mm-dd")

	return _make_api_call("tc", key=date, param="fecha", cache=cache)