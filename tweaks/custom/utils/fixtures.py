import os

import frappe
import frappe.utils
import frappe.utils.fixtures
from frappe.core.doctype.data_import.data_import import export_json


def export_fixtures(app=None):
    """
    Export fixtures as JSON to `[app]/fixtures`

    Patched: allow setting `order_by` property
    """
    if app:
        apps = [app]
    else:
        apps = frappe.get_installed_apps()
    for app in apps:
        for fixture in frappe.get_hooks("fixtures", app_name=app):
            filters = None
            or_filters = None
            order_by = None
            if isinstance(fixture, dict):
                filters = fixture.get("filters")
                or_filters = fixture.get("or_filters")
                order_by = fixture.get("order_by")
                fixture = fixture.get("doctype") or fixture.get("dt")
            print(
                f"Exporting {fixture} app {app} filters {(filters if filters else or_filters)}"
            )
            if not os.path.exists(frappe.get_app_path(app, "fixtures")):
                os.mkdir(frappe.get_app_path(app, "fixtures"))

            export_json(
                fixture,
                frappe.get_app_path(app, "fixtures", frappe.scrub(fixture) + ".json"),
                filters=filters,
                or_filters=or_filters,
                order_by=order_by or "idx asc, creation asc",
            )


def apply_fixtures_patches():
    frappe.utils.fixtures.export_fixtures = export_fixtures
