"""
Concurrent utilities for Frappe applications.

This module provides utilities for running functions in concurrent threads while
preserving Frappe's site context, user sessions, and language settings.
"""

from concurrent.futures import ThreadPoolExecutor

import frappe
from frappe import connect, destroy, init, set_user, set_user_lang


class init_site:
    """
    Context manager for initializing Frappe site context.

    This class provides a context manager that properly initializes a Frappe site
    with the specified user and language settings, and ensures proper cleanup
    when exiting the context.

    Args:
        site (str, optional): Site name. Defaults to empty string.
        user (str, optional): User to set in the session. Defaults to "Administrator".
        lang (str, optional): Language to set for the user. Defaults to None.

    Example:
        with init_site(site="mysite.com", user="user@example.com"):
            # Frappe context is now available
            doc = frappe.get_doc("User", "user@example.com")
    """

    def __init__(self, site=None, user=None, lang=None):
        self.site = site or ""
        self.user = user or "Administrator"
        self.lang = lang

    def __enter__(self):
        """
        Enter the context manager and initialize Frappe site context.

        Initializes the site, establishes database connection, sets the user,
        and configures the user's language preference.

        Returns:
            self: The context manager instance.
        """
        init(self.site)
        connect()
        set_user(self.user)
        set_user_lang(self.user, self.lang)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and clean up Frappe context.

        Destroys the Frappe context, closing database connections and
        clearing session data.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        destroy()


def get_context_runner(site=None, user=None, lang=None):
    """
    Get a runner function that executes with proper Frappe context.

    Creates a function that can be used to execute other functions while
    maintaining proper Frappe site context, user session, and language settings.

    Args:
        site (str, optional): Site name. Uses current site if not provided.
        user (str, optional): User for the session. Uses current user if not provided.
        lang (str, optional): Language preference. Defaults to None.

    Returns:
        callable: A function that executes the given function with Frappe context.

    Example:
        runner = get_context_runner(site="mysite.com", user="admin@example.com")
        result = runner(some_function, arg1, arg2, kwarg1="value")
    """

    # Capture current context
    site = site or frappe.local.site
    user = user or frappe.session.user

    def run_with_site_context(func, *args, **kwargs):
        """
        Execute function with proper Frappe context.

        Wraps the function execution within a Frappe site context, ensuring
        that database connections, user sessions, and language settings are
        properly initialized before function execution.

        Args:
            func (callable): The function to execute.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Any: The result of the function execution.
        """
        with init_site(site=site, user=user, lang=lang):
            return func(*args, **kwargs)

    return run_with_site_context


class ThreadPoolExecutorWithContext:
    """
    ThreadPoolExecutor that preserves Frappe context in each thread.

    This class extends the functionality of ThreadPoolExecutor by automatically
    preserving Frappe site context, user sessions, and language settings when
    executing functions in worker threads.

    Args:
        max_workers (int, optional): Maximum number of worker threads.
            If None, uses ThreadPoolExecutor default.
        site (str, optional): Site name to use in worker threads.
            Uses current site if not provided.
        user (str, optional): User for sessions in worker threads.
            Uses current user if not provided.
        lang (str, optional): Language preference for worker threads.
            Defaults to None.

    Example:
        with ThreadPoolExecutorWithContext(max_workers=4, site="mysite.com") as executor:
            future = executor.submit(frappe_function, arg1, arg2)
            result = future.result()
    """

    def __init__(self, max_workers=None, site=None, user=None, lang=None):
        self.context_runner = get_context_runner(site=site, user=user, lang=lang)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def __enter__(self):
        """
        Enter the context manager.

        Returns:
            ThreadPoolExecutorWithContext: The executor instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context manager and shutdown the thread pool.

        Waits for all submitted tasks to complete before shutting down
        the underlying ThreadPoolExecutor.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        self.executor.shutdown(wait=True)

    def submit(self, fn, *args, **kwargs):
        """
        Submit a function to be executed with preserved Frappe context.

        Submits the function to the thread pool for execution, automatically
        wrapping it with the context runner to preserve Frappe site context,
        user session, and language settings.

        Args:
            fn (callable): The function to execute in a worker thread.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            Future: A Future object representing the execution of the function.

        Example:
            future = executor.submit(frappe.get_doc, "User", "user@example.com")
            doc = future.result()  # Get the result when ready
        """
        return self.executor.submit(self.context_runner, fn, *args, **kwargs)
