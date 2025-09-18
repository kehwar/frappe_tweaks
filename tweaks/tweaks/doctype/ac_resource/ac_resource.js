// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Resource", {
	setup(frm) {
        frm.trigger('setup_help');
	},
    refresh(frm) {
        frm.trigger("script_type");
        frm.trigger("show_api_warning");
    },
    setup_help(frm) {
        frm.get_field('actions_html').html(`
            <p class="help-box small text-muted">
            A <code>user</code> will have access to this <code>resource</code> if <b>at least one</b> <code>rule</code> permits it and <b>zero</b> <code>rules</code> forbid it.
            <br>Unmanaged <code>actions</code> are not subject to any <code>rule</code> and are allowed by default.
            </p>`
        );
    },
    type(frm){
        frm.trigger("show_api_warning");
    },
    setup_python_help(frm) {
        frm.get_field('script_html').html(`
            <p class="help-box small text-muted">
                Example:
                <code>
                conditions = f'tenant_id = {tenant_id}'
                </code>
            </p>`
        );
    },
    setup_sql_help(frm) {
        frm.get_field('script_html').html(`
            <p class="help-box small text-muted">
                Example:
                <code>
                tenant_id = 1
                </code>
            </p>`
        );
    },
    setup_script_help(frm){
        if (frm.doc.script_type == "SQL")
            frm.trigger('setup_sql_help');
        else
            frm.trigger('setup_python_help');
    },
    script_type(frm) {
        frm.trigger('setup_script_help');
        frm.get_field('condition_script').df.options = frm.doc.script_type || "Python";
        if (frm.get_field('condition_script').editor)
            frm.get_field('condition_script').set_language();
    },
    show_api_warning(frm) {
        frm.dashboard.clear_headline();
        if (["DocType", "Report", "Custom"].includes(frm.doc.type))
            frm.set_intro(_(`
                The API doesn't manage pemission automatically for <code>${frm.doc.type}</code> resources.
                You must get the filter query using <code>tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_resource_filter_query</code> function and apply it manually.
                <br>Example: <code>
                    frappe.call('tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_resource_filter_query', ${frappe.scrub(frm.doc.type)}="${frappe.scrub(frm.doc.type)}name", fieldname="", action="Read")
                </code>
            `), "yellow")
    }
});