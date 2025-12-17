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
        "tweaks.custom.doctype.pricing_rule.install_pricing_rule_customizations",
        "tweaks.custom.doctype.user_group.apply_user_group_patches",
        "tweaks.custom.doctype.role.apply_role_patches",
        "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.after_install",
    ]
    + workflow_script_hooks["after_install"]
    + server_script_hooks["after_install"]
)

doc_events = {
    "*": {
        "on_change": workflow_script_hooks["doc_events"]["*"]["on_change"],
    },
    "Customer": {
        "before_validate": "tweaks.custom.doctype.customer.before_validate",
        "validate": "tweaks.custom.doctype.customer.validate",
        "on_update": "tweaks.custom.doctype.customer.on_update",
    },
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

override_doctype_class = {
    "Reminder": "tweaks.custom.doctype.reminder.TweaksReminder",
    "Server Script": "tweaks.custom.doctype.server_script.TweaksServerScript",
}

get_product_discount_rule = [
    "tweaks.custom.doctype.pricing_rule.get_product_discount_rule"
]

apply_pricing_rule_on_transaction = [
    "tweaks.custom.doctype.pricing_rule.apply_pricing_rule_on_transaction"
]

# Scheduled Tasks
scheduler_events = {
    "cron": {
        "30 */6 * * *": [
            "tweaks.tweaks.doctype.peru_api_com.peru_api_com.autoupdate_currency_exchange"
        ]
    },
    "all": ["tweaks.utils.sync_job.auto_retry_failed_jobs"],
}


safe_exec_globals = ["tweaks.utils.safe_exec.safe_exec_globals"]

safe_eval_globals = ["tweaks.utils.safe_exec.safe_eval_globals"]

website_route_rules = [
    {"from_route": "/h/<file_name>", "to_route": "html-file"},
]
