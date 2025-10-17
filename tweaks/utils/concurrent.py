from concurrent.futures import ThreadPoolExecutor

import frappe
from frappe import connect, destroy, init, set_user, set_user_lang


class init_site:
    def __init__(self, site=None, user=None, lang=None):
        self.site = site or ""
        self.user = user or "Administrator"
        self.lang = lang

    def __enter__(self):
        init(self.site)
        connect()
        set_user(self.user)
        set_user_lang(self.user, self.lang)

    def __exit__(self, type, value, traceback):
        destroy()


def get_context_runner(site=None, user=None, lang=None):
    """Get a runner function that executes with proper Frappe context"""

    # Capture current context
    site = site or frappe.local.site
    user = user or frappe.session.user

    def run_with_site_context(func, *args, **kwargs):
        """Execute function with proper Frappe context using site_in_thread"""
        with init_site(site=site, user=user, lang=lang):
            return func(*args, **kwargs)

    return run_with_site_context


class ThreadPoolExecutorWithContext:
    """ThreadPoolExecutor that preserves Frappe context in each thread"""

    def __init__(self, max_workers=None, site=None, user=None, lang=None):
        self.context_runner = get_context_runner(site=site, user=user, lang=lang)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)

    def submit(self, fn, *args, **kwargs):
        """Submit a function to be executed with preserved Frappe context"""
        return self.executor.submit(self.context_runner, fn, *args, **kwargs)
