import re
import traceback

import frappe
import yaml
from frappe import _
from frappe.core.doctype.version.version import get_diff
from frappe.desk.doctype.notification_log.notification_log import (
    send_notification_email,
)
from frappe.model.naming import getseries
from frappe.utils import safe_exec
from frappe.utils.safe_exec import NamespaceDict, call_whitelisted_function
from frappe.utils.xlsxutils import (
    read_xls_file_from_attached_file,
    read_xlsx_file_from_attached_file,
)

from tweaks.custom.utils.formatter import to_snake_case
from tweaks.custom.utils.naming import setseries
from tweaks.tweaks.doctype.open_observe_api.open_observe_api import (
    search_logs,
    send_logs,
)
from tweaks.tweaks.doctype.peru_api_com.peru_api_com import (
    get_dni,
    get_ruc,
    get_ruc_suc,
    get_rut,
    get_tc,
)


def admin_sql(query, *args, **kwargs):
    """a wrapper for frappe.db.sql to allow only for admin"""
    if frappe.session.user != "Administrator":
        frappe.throw(
            _("Must be Administrator to run this query"),
            title=_("Unsafe SQL query"),
            exc=frappe.PermissionError,
        )

    return frappe.db.sql(query, *args, **kwargs)


def get_re_module():
    return NamespaceDict(
        match=re.match,
        search=re.search,
        findall=re.findall,
        finditer=re.finditer,
        sub=re.sub,
        subn=re.subn,
        split=re.split,
        fullmatch=re.fullmatch,
        compile=re.compile,
        escape=re.escape,
        purge=re.purge,
        DOTALL=re.DOTALL,
        IGNORECASE=re.IGNORECASE,
        MULTILINE=re.MULTILINE,
        VERBOSE=re.VERBOSE,
        ASCII=re.ASCII,
        LOCALE=re.LOCALE,
        UNICODE=re.UNICODE,
        DEBUG=re.DEBUG,
    )


def get_cache_module():
    return NamespaceDict(
        set_value=frappe.cache.set_value,
        get_value=frappe.cache.get_value,
        delete_value=frappe.cache.delete_value,
        hset=frappe.cache.hset,
        hget=frappe.cache.hget,
        hgetall=frappe.cache.hgetall,
        hdel=frappe.cache.hdel,
    )


def safe_exec_globals(out):

    out.frappe.update(
        {
            "cache": get_cache_module(),
            "call": call_whitelisted_function,
            "debug_log": frappe.debug_log,
            "get_roles": frappe.get_roles,
            "get_traceback": frappe.get_traceback,
            "has_permission": frappe.has_permission,
            "only_for": frappe.only_for,
            "set_user": frappe.set_user,
            "desk": NamespaceDict(
                notification_log=NamespaceDict(
                    send_notification_email=send_notification_email
                ),
            ),
            "get_diff": get_diff,
        }
    )

    out.frappe.db.update(
        {
            "unsafe_sql": admin_sql,
        }
    )

    out.frappe.utils.update(
        {
            "getseries": getseries,
            "setseries": setseries,
            "to_snake_case": to_snake_case,
        }
    )

    out.update(
        {
            "locals": locals,
            "re": get_re_module(),
            "safe_exec": safe_exec.safe_exec,
            "traceback": NamespaceDict(format_stack=traceback.format_stack),
            "xlsxutils": NamespaceDict(
                read_xlsx_file_from_attached_file=read_xlsx_file_from_attached_file,
                read_xls_file_from_attached_file=read_xls_file_from_attached_file,
            ),
            "yaml": NamespaceDict(load=yaml.safe_load, dump=yaml.safe_dump),
            "peru_api_com": NamespaceDict(
                get_ruc=get_ruc,
                get_dni=get_dni,
                get_tc=get_tc,
                get_ruc_suc=get_ruc_suc,
                get_rut=get_rut,
            ),
            "open_observe": NamespaceDict(
                send_logs=send_logs,
                search_logs=search_logs,
            ),
        }
    )


def safe_eval_globals(out):

    return safe_exec.get_safe_globals()
