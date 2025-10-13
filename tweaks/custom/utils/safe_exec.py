import re
import traceback

import frappe
import yaml
from frappe import (_, debug_log)
from frappe.desk.doctype.notification_log.notification_log import (
    send_notification_email,
)
from frappe.model.naming import getseries
from frappe.utils import safe_exec
from frappe.utils.safe_exec import NamespaceDict
from tweaks.custom.utils.formatter import to_snake_case
from tweaks.custom.utils.naming import setseries
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, read_xls_file_from_attached_file
from frappe.utils.safe_exec import call_whitelisted_function


def set_nested_dict(d, key, value):
    keys = key.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, frappe._dict({}))  # Ensure nested dictionaries exist
    d[keys[-1]] = value


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


def get_safe_globals(get_safe_globals):
    # TODO: Consider lazy loading modules instead of creating all overrides upfront for better memory usage

    def _get_safe_globals():

        globals = get_safe_globals()

        # TODO: Cache these module namespaces at site level to avoid rebuilding on every execution
        overrides = {
            "frappe.cache": get_cache_module(),
            "frappe.call": call_whitelisted_function,
            "frappe.desk.notification_log.send_notification_email": send_notification_email,
            "frappe.db.unsafe_sql": admin_sql,
            "frappe.debug_log": frappe.debug_log,
            "frappe.get_roles": frappe.get_roles,
            "frappe.get_traceback": frappe.get_traceback,
            "frappe.has_permission": frappe.has_permission,
            "frappe.only_for": frappe.only_for,
            "frappe.set_user": frappe.set_user,
            "frappe.utils.getseries": getseries,
            "frappe.utils.setseries": setseries,
            "frappe.utils.to_snake_case": to_snake_case,
            "locals": locals,
            "re": get_re_module(),
            "safe_exec": safe_exec.safe_exec,
            "traceback.format_stack": traceback.format_stack,
            "xlsxutils.read_xlsx_file_from_attached_file": read_xlsx_file_from_attached_file,
            "xlsxutils.read_xls_file_from_attached_file": read_xls_file_from_attached_file,
            "yaml": NamespaceDict(load=yaml.safe_load, dump=yaml.safe_dump),
        }

        for key, method in overrides.items():
            set_nested_dict(globals, key, method)

        hook_utils = frappe.get_hooks("safe_exec_globals")
        if hook_utils:
            for key, method in hook_utils.items():
                method = frappe.get_attr(method[-1])
                set_nested_dict(globals, key, method)

        return globals

    return _get_safe_globals


def safe_eval(safe_eval, get_safe_globals):

    def _safe_eval(code, eval_globals=None, eval_locals=None):

        _globals = get_safe_globals()
        if eval_globals:
            _globals.update(eval_globals)

        return safe_eval(code, _globals, eval_locals)

    return _safe_eval


def apply_safe_exec_patches():
    safe_exec.get_safe_globals = get_safe_globals(safe_exec.get_safe_globals)
    safe_exec.safe_eval = safe_eval(safe_exec.safe_eval, safe_exec.get_safe_globals)
