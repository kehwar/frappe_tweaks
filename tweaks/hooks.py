# App data

app_name = "tweaks"
app_title = "Tweaks"
app_publisher = "Erick W.R."
app_description = "Tweaks for Frappe"
app_email = "erickkwr@gmail.com"
app_license = "mit"
required_apps = ["kehwar/frappe", "kehwar/erpnext"]

# Hooks

app_include_js = "frappe_tweaks.bundle.js"

after_install = [
    "tweaks.custom.doctype.pricing_rule.install_pricing_rule_customizations",
    "tweaks.custom.doctype.user_group.apply_user_group_patches",
    "tweaks.custom.doctype.role.apply_role_patches",
    "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.after_install",
]

after_migrate = [
    "tweaks.utils.sync_job_type.sync_job_types",
    "tweaks.utils.report.clean_reports_with_missing_modules",
]

doc_events = {
    "*": {
        "on_change": ["tweaks.utils.document_review.evaluate_document_reviews"],
        "before_transition": [
            "tweaks.utils.workflow.check_workflow_transition_permission"
        ],
        "before_submit": ["tweaks.utils.document_review.check_mandatory_reviews"],
    },
    "Customer": {
        "before_validate": "tweaks.custom.doctype.customer.before_validate",
        "validate": "tweaks.custom.doctype.customer.validate",
        "on_update": "tweaks.custom.doctype.customer.on_update",
    },
}

permission_query_conditions = {
    "*": [
        "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_permission_query_conditions"
    ],
    "Workflow Action": [
        "tweaks.utils.workflow.get_workflow_action_permission_query_conditions"
    ],
}

write_permission_query_conditions = {
    "*": [
        "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_write_permission_query_conditions"
    ]
}

override_doctype_class = {
    "Reminder": "tweaks.custom.doctype.reminder.TweaksReminder",
}

get_product_discount_rule = [
    "tweaks.custom.doctype.pricing_rule.get_product_discount_rule"
]

apply_pricing_rule_on_transaction = [
    "tweaks.custom.doctype.pricing_rule.apply_pricing_rule_on_transaction"
]

# Workflow hooks
filter_workflow_transitions = ["tweaks.utils.workflow.filter_transitions_by_ac_rules"]

has_workflow_action_permission = [
    "tweaks.utils.workflow.has_workflow_action_permission_via_ac_rules"
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

ignore_links_on_delete = [
    "Sync Job",
    "Sync Job Type",
]


safe_exec_globals = ["tweaks.utils.safe_exec.safe_exec_globals"]

safe_eval_globals = ["tweaks.utils.safe_exec.safe_eval_globals"]

auth_hooks = ["tweaks.custom.utils.authentication.validate_user_password"]

website_route_rules = [
    {"from_route": "/h/<file_name>", "to_route": "html-file"},
]

# Timeline hooks
additional_timeline_content = {
    "*": ["tweaks.utils.document_review.get_document_reviews_for_timeline"]
}
