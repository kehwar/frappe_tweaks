from tweaks.custom.utils.hooks import join_doc_events
from tweaks.tweaks.doctype.event_script.event_script import event_script_hooks

# App data

app_name = "tweaks"
app_title = "Tweaks"
app_publisher = "Erick W.R."
app_description = "Tweaks for Frappe"
app_email = "erickkwr@gmail.com"
app_license = "mit"

# Hooks

after_install = "tweaks.tweaks.doctype.server_performance_log.install.after_install"

before_uninstall = (
    "tweaks.tweaks.doctype.server_performance_log.install.before_uninstall"
)

doc_events = {
    "*": {
        "on_change": event_script_hooks["doc_events"]["*"]["on_change"],
        "after_rename": event_script_hooks["doc_events"]["*"]["after_rename"],
    }
}

has_permission = event_script_hooks["has_permission"]

permission_query_conditions = event_script_hooks["permission_query_conditions"]


# Scheduler

scheduler_events = {
    "cron": {
        "* * * * *": [
            "tweaks.tweaks.doctype.server_performance_log.server_performance_log_task.execute"
        ]
    },
}
