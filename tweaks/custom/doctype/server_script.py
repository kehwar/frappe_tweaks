import frappe
from frappe import _
from frappe.core.doctype.server_script.server_script import ServerScript
from frappe.desk.form.meta import FormMeta
from frappe.modules import scrub


class TweaksServerScript(ServerScript):

    def before_validate(self):

        if self.script_type != "DocType Event":
            self.doctype_event = ""
        if self.event_frequency != "Cron":
            self.cron_format = ""
        if self.script_type != "API":
            self.api_method = ""
        if self.script_type not in (
            "DocType Event",
            "Permission Policy",
            "Permission Query",
        ):
            self.reference_doctype = ""
        if self.script_type != "Scheduler Event":
            self.event_frequency = ""

    def validate(self):

        super().validate()

        if self.script_type == "DocType Event" and not self.doctype_event:
            frappe.throw(_("DocType Event is required"))

        if (
            self.script_type
            in ("DocType Event", "Permission Policy", "Permission Query")
            and not self.reference_doctype
        ):
            frappe.throw(_("Reference DocType is required"))
