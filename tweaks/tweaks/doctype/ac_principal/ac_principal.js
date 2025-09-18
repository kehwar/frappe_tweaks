// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Principal", {
	refresh(frm) {
        frm.trigger('setup_script_help');
	},
    setup_python_help(frm) {
        frm.get_field('script_html').html(`
            <p class="help-box small text-muted">
                Example:<code>
                conditions = f"""\`tabUser\`.\`name\` in ({frappe.get_all('Item', fields=['owner'], order_by="", distinct=1, run=0)})"""
                </code>
            </p>`
        );
    },
    setup_sql_help(frm) {
        frm.get_field('script_html').html(`
            <p class="help-box small text-muted">
                Example:<code>
                \`tabUser\`.\`name\` IN (SELECT \`owner\` FROM \`tabItem\`)
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
    }
});


