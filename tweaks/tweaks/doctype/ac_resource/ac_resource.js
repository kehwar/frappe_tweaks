// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Resource", {
	setup(frm) {
        frm.trigger('setup_help');
	},
    setup_help(frm) {
        frm.get_field('actions_html').html(`
            <p class="help-box small text-muted">
            A <code>user</code> will have access to this <code>resource</code> if <b>at least one</b> <code>rule</code> permits it and <b>zero</b> <code>rules</code> forbid it.
            <br>Unmanaged <code>actions</code> are not subject to any <code>rule</code> and are allowed by default.
            </p>`
        );
    }
});