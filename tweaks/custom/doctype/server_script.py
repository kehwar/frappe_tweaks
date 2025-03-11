import frappe
from frappe import _
from frappe.core.doctype.server_script.server_script import ServerScript
from frappe.desk.form.meta import FormMeta
from frappe.modules import scrub
from frappe.utils.safe_exec import (
    FrappeTransformer,
    get_keys_for_autocomplete,
    get_safe_globals,
    is_safe_exec_enabled,
    safe_exec,
)


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

    def get_permission_policy(self, user, ptype=None, doc=None):

        locals = {
            "user": user,
            "ptype": ptype or "select",
            "doc": doc,
            "allow": None,
            "filters": None,
            "or_filters": None,
            "query": None,
            "message": None,
        }

        safe_exec(self.script, None, locals, script_filename=self.name)

        if locals["filters"] or locals["or_filters"]:

            locals["query"] = frappe.db.get_all(
                self.reference_doctype,
                filters=locals["filters"],
                or_filters=locals["or_filters"],
                run=False,
                distinct=True,
                order_by="",
            )

        if locals["query"] or locals["allow"] is not None:

            return frappe._dict(
                {
                    "allow": (
                        True if locals["allow"] is None or locals["allow"] else False
                    ),
                    "filters": locals["filters"],
                    "or_filters": locals["or_filters"],
                    "message": locals["message"],
                    "query": locals["query"],
                }
            )
