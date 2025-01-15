app_name = "tweaks"
app_title = "Tweaks"
app_publisher = "Erick W.R."
app_description = "Tweaks for Frappe"
app_email = "erickkwr@gmail.com"
app_license = "mit"


after_install = "tweaks.tweaks.doctype.server_performance_log.install.after_install"
before_uninstall = (
    "tweaks.tweaks.doctype.server_performance_log.install.before_uninstall"
)

scheduler_events = {
    "cron": {
        "* * * * *": [
            "tweaks.tweaks.doctype.server_performance_log.server_performance_log_task.execute"
        ]
    },
}
