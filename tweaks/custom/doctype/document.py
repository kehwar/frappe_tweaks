from frappe.core.doctype.server_script.server_script_utils import (
    run_server_script_for_doc_event,
)
from frappe.integrations.doctype.webhook import run_webhooks
from frappe.model.document import Document
from tweaks.tweaks.doctype.event_script.event_script import (
    run_method as run_event_script_method,
)


def run_method(self, method, *args, **kwargs):
    """run standard triggers, plus those in hooks"""

    self.flags.run_method = method
    self.flags.run_method_args = args
    self.flags.run_method_kwargs = kwargs

    def fn(self, *args, **kwargs):
        method_object = getattr(self, method, None)

        # Cannot have a field with same name as method
        # If method found in __dict__, expect it to be callable
        if method in self.__dict__ or callable(method_object):
            return method_object(*args, **kwargs)

    fn.__name__ = str(method)
    out = Document.hook(fn)(self, *args, **kwargs)

    self.run_notifications(method)
    run_webhooks(self, method)
    run_server_script_for_doc_event(self, method)

    run_event_script_method(self, method, *args, **kwargs)  # Deprecated

    self.flags.pop("run_method", None)
    self.flags.pop("run_method_args", None)
    self.flags.pop("run_method_kwargs", None)

    return out


def get_method_args(self):
    return getattr(self, "_run_method_args", None)


def get_method_kwargs(self):
    return getattr(self, "_run_method_kwargs", None)


def apply_document_patches():

    Document.run_method = run_method
    Document.get_method_args = get_method_args
    Document.get_method_kwargs = get_method_kwargs
