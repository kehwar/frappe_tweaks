import re
import traceback

import frappe
import yaml
from frappe import _
from frappe.model.naming import getseries
from frappe.utils import safe_exec
from frappe.utils.safe_exec import NamespaceDict
from tweaks.custom.utils.formatter import to_snake_case
from tweaks.custom.utils.naming import setseries


def log_traceback():

    stack_trace = "".join(traceback.format_stack())
    frappe.log_error("stack", stack_trace)


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

    def _get_safe_globals():

        globals = get_safe_globals()

        overrides = {
            "frappe.cache": get_cache_module(),
            "frappe.db.unsafe_sql": admin_sql,
            "frappe.get_roles": frappe.get_roles,
            "frappe.has_permission": frappe.has_permission,
            "frappe.utils.getseries": getseries,
            "frappe.utils.setseries": setseries,
            "frappe.utils.to_snake_case": to_snake_case,
            "re": get_re_module(),
            "safe_exec": safe_exec.safe_exec,
            "traceback.format_stack": traceback.format_stack,
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


def apply_safe_exec_patches():
    safe_exec.get_safe_globals = get_safe_globals(safe_exec.get_safe_globals)
    safe_exec.WHITELISTED_SAFE_EVAL_GLOBALS["len"] = len
    safe_exec.WHITELISTED_SAFE_EVAL_GLOBALS["re"] = get_re_module()
