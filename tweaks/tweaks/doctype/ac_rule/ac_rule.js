// Copyright (c) 2025, Erick W.R. and contributors
// For license information, please see license.txt

frappe.ui.form.on("AC Rule", {
	setup(frm) {
        frm.trigger('setup_help');
	},
    setup_help(frm) {
        frm.get_field('principals_html').html(`
            <p class="help-box small text-muted">
            This <code>rule</code> will apply to <code>users</code> <b>matching any</b> <code>principal</code> listed and <b>not matching any</b> <code>exception</code> listed
            <br><i>Example: (M1 OR M2) AND !(E1 OR E2)</i>
            </p>`
        );
        frm.get_field('resources_html').html(`
            <p class="help-box small text-muted">
            This <code>rule</code> will apply to <code>records</code> <b>matching any</b> <code>resource</code> listed and <b>not matching any</b> <code>exception</code> listed
            <br><i>Example: (M1 OR M2) AND !(E1 OR E2)</i>
            </p>`
        );
        frm.get_field('type_html').html(`
            <p class="help-box small text-muted">
            A <code>user</code> will have access to a <code>resource</code> if <b>at least one</b> <code>rule</code> permits it and <b>zero</b> <code>rules</code> forbid it.
            </p>`
        );
    }
});


