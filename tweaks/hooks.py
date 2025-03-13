from tweaks.custom.doctype.client_script import client_script_hooks
from tweaks.custom.doctype.server_script_customization import server_script_hooks
from tweaks.custom.doctype.workflow import workflow_script_hooks
from tweaks.custom.utils.permissions import permission_hooks
from tweaks.tweaks.doctype.event_script.event_script import event_script_hooks

# App data

app_name = "tweaks"
app_title = "Tweaks"
app_publisher = "Erick W.R."
app_description = "Tweaks for Frappe"
app_email = "erickkwr@gmail.com"
app_license = "mit"

# Hooks

app_include_js = "frappe_tweaks.bundle.js"

after_install = (
    [
        "tweaks.tweaks.doctype.server_performance_log.install.after_install",
    ]
    + workflow_script_hooks["after_install"]
    + client_script_hooks["after_install"]
    + server_script_hooks["after_install"]
)

before_uninstall = (
    "tweaks.tweaks.doctype.server_performance_log.install.before_uninstall"
)

doc_events = {
    "*": {
        "on_change": workflow_script_hooks["doc_events"]["*"]["on_change"],
    }
}

has_permission = {
    "*": (
        event_script_hooks["has_permission"]["*"]
        + permission_hooks["has_permission"]["*"]
    )
}

permission_query_conditions = {
    "*": (
        event_script_hooks["permission_query_conditions"]["*"]
        + permission_hooks["permission_query_conditions"]["*"]
    )
}

override_whitelisted_methods = {
    "frappe.desk.form.utils.get_next": f"tweaks.custom.utils.virtual_doctype.get_next"
}

override_doctype_class = {
    "Client Script": "tweaks.custom.doctype.client_script.TweaksClientScript",
    "Server Script": "tweaks.custom.doctype.server_script.TweaksServerScript",
}

# Scheduler

scheduler_events = {
    "cron": {
        "* * * * *": [
            "tweaks.tweaks.doctype.server_performance_log.server_performance_log_task.execute"
        ]
    },
}
